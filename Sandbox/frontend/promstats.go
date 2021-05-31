package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/knix-microfunctions/knix/Sandbox/frontend/containerstats"
)

var username string 
var workflowname string 
var inFlightRequestsCounterChan chan int
var promHandler http.Handler

var lastMetricsTimestamp uint64
var lastMetricsCpuUsageTotalNanosecond uint64
var lastMetricsCpuUsageUserNanosecond uint64
var lastMetricsCpuUsageSystemNanosecond uint64
var lastMetricsCpuThrottledNanosecond uint64
//var lastMetricsCpuThrottledPeriods uint64
//var lastMetricsCpuPeriods uint64

func GetEnvWithDefault(key string, defaultVal string) string {
    var val = defaultVal
    envVal, ok := os.LookupEnv(key)
    if ok {
        val = envVal
    }
    return val
}

var workflow_requests_started_count = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_requests_started_count",
	Help: "The number of knix workflow requests started",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_requests_finished_count = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_requests_finished_count",
	Help: "The number of knix workflow requests finished",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_requests_in_flight_count = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_requests_in_flight_count",
	Help: "The number of knix workflow requests in flight",
    },
	[]string{"knix_user", "knix_workflow",})

// The size in bytes of anonymous and swap cache on active least-recently-used (LRU) list (includes tmpfs)
var workflow_memory_rss_mb = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_memory_rss_mb",
	Help: "The size in mega bytes of rss memory (anonymous and swap cache on active least-recently-used (LRU) list (includes tmpfs)) consumed by a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})


var workflow_memory_cache_mb = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_memory_cache_mb",
	Help: "The size in mega bytes of page cache (includes tmpfs) memory consumed by a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_memory_mapped_file_mb = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_memory_mapped_file_mb",
	Help: "The size in mega bytes of memory-mapped files (includes tmpfs) consumed by a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_process_count = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_process_count",
	Help: "The number of processes running inside a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_total_sec = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_total_sec",
	Help: "The total CPU time in seconds for all processes inside a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_total_percentage = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_total_percentage",
	Help: "The total usage CPU in percentage for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_user_sec = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_user_sec",
	Help: "The user space CPU time in seconds for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_user_percentage = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_user_percentage",
	Help: "The user space usage CPU in percentage for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_system_sec = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_system_sec",
	Help: "The kernel space CPU time in seconds for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_system_percentage = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_system_percentage",
	Help: "The kernel space usage CPU in percentage for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_throttled_sec = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_throttled_sec",
	Help: "The cpu throttled time in seconds for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_throttled_percentage = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_throttled_percentage",
	Help: "The cpu throttled time in percentage for all processes inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_throttled_periods_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_throttled_periods_total",
	Help: "The total number of runnable periods in which a thread used its entire quota and was throttled inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_periods_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_periods_total",
	Help: "The total number of periods that any thread inside a knix sandbox was runnable ",
	},
	[]string{"knix_user", "knix_workflow",})
	

var workflow_net_tcpext_listen_drops_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcpext_listen_drops_total",
	Help: "The total number TcpExtListenDrops inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcpext_listen_overflows_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcpext_listen_overflows_total",
	Help: "The total number TcpExtListenOverflows inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_backlog_drops_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_backlog_drops_total",
	Help: "The total number TCPBacklogDrop inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_abort_on_memory_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_abort_on_memory_total",
	Help: "The total number TCPAbortOnMemory inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_active_opens_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_active_opens_total",
	Help: "The total number TCP ActiveOpens inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_passive_opens_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_passive_opens_total",
	Help: "The total number TCP PassiveOpens inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})
	
var workflow_net_sockets_used_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_sockets_used_total",
	Help: "The total number sockstats sockets used inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_inuse_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_inuse_total",
	Help: "The total number sockstats TCP inuse counter inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_orphan_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_orphan_total",
	Help: "The total number sockstats TCP orphan counter inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_tw_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_tw_total",
	Help: "The total number sockstats TCP tw counter inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_alloc_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_alloc_total",
	Help: "The total number sockstats TCP alloc counter inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})

var workflow_net_tcp_mem_total = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_net_tcp_mem_total",
	Help: "The total number sockstats TCP mem counter inside a knix sandbox",
	},
	[]string{"knix_user", "knix_workflow",})
	

func handle_metrics(w http.ResponseWriter, r *http.Request) {
	updateResourceStats()
	promHandler.ServeHTTP(w, r)
}

func initResourceStats() {
	inFlightRequestsCounterChan = make(chan int, 2000)
	go inFlightRequestsCounter(inFlightRequestsCounterChan)
	username = GetEnvWithDefault("USERID", "__knix_user_not_set__")
	workflowname = GetEnvWithDefault("WORKFLOWNAME", "__knix_workflow_not_set__")
	promHandler = promhttp.Handler()
	workflow_requests_in_flight_count.WithLabelValues(username, workflowname).Set(0.0)
	workflow_requests_started_count.WithLabelValues(username, workflowname).Set(0.0)
	workflow_requests_finished_count.WithLabelValues(username, workflowname).Set(0.0)

	updateResourceStats()
}

func updateMemoryStats() string {
	memoryStats := make(map[string]uint64)
	err := containerstats.GetMemoryStats(memoryStats)
	if err != nil {
		fmt.Println("Error getting memory stats. Ignoring", err.Error())
		return ""
	}

	var ( 
		total_rss = float64(memoryStats["total_rss"])/(1024.0*1024.0)
		total_cache = float64(memoryStats["total_cache"])/(1024.0*1024.0)
		total_mapped_file = float64(memoryStats["total_mapped_file"])/(1024.0*1024.0)
	)	
	workflow_memory_rss_mb.WithLabelValues(username, workflowname).Set(total_rss)
	workflow_memory_cache_mb.WithLabelValues(username, workflowname).Set(total_cache)
	workflow_memory_mapped_file_mb.WithLabelValues(username, workflowname).Set(total_mapped_file)
	statString := fmt.Sprintf("memory_rss_mb,%.6f,memory_cache_mb,%.6f,memory_mapped_file_mb,%.6f",total_rss, total_cache,total_mapped_file)
	//fmt.Println("memory", statString)
	return statString
}

func updatePidsStats() string {
	var numberOfProcesses uint64
	err := containerstats.GetNumberOfProcesses(&numberOfProcesses)
	if err != nil {
		fmt.Println("Error getting number of pids. Ignoring", err.Error())
		return ""
	}

	workflow_process_count.WithLabelValues(username, workflowname).Set(float64(numberOfProcesses))
	statString := fmt.Sprintf("pids,%d",numberOfProcesses)
	//fmt.Println("pids", numberOfProcesses)
	return statString
}

func updateCpuStats() string {
	var (
		nanosecondUserCpuactUsage uint64 
		nanosecondSystemCpuactUsage uint64
		nanosecondTotalCpuactUsage uint64
	)
	err := containerstats.GetSplitCpuactUsageNanoseconds(
		&nanosecondUserCpuactUsage, 
		&nanosecondSystemCpuactUsage, 
		&nanosecondTotalCpuactUsage,
	)
	//err = containerstats.GetCpuactUsageNanoseconds(&nanosecondTotalCpuactUsage)
	if err != nil {
		fmt.Println("Error getting cpu usage. Ignoring", err.Error())
		return ""
	}

	throttlingStats := make(map[string]uint64)
	err = containerstats.GetCpuThrottlingStats(throttlingStats)
	if err != nil {
		fmt.Println("Error getting cpu throttling info. Ignoring", err.Error())
		return ""
	}

	var (
		nanosecondThrottledNanosecond uint64 = throttlingStats["throttled_time"]
		numberPeriods float64 = float64(throttlingStats["nr_periods"])
		numberThrottledPeriods float64 = float64(throttlingStats["nr_throttled"])
	)

	now := uint64(time.Now().UnixNano())
	if lastMetricsCpuUsageTotalNanosecond == 0 || lastMetricsTimestamp == 0 {
		lastMetricsCpuUsageTotalNanosecond = nanosecondTotalCpuactUsage
		lastMetricsCpuUsageUserNanosecond = nanosecondUserCpuactUsage
		lastMetricsCpuUsageSystemNanosecond = nanosecondSystemCpuactUsage
		lastMetricsCpuThrottledNanosecond = nanosecondThrottledNanosecond
		lastMetricsTimestamp = now
	}

	cpuNanosecondTotalDiff := nanosecondTotalCpuactUsage - lastMetricsCpuUsageTotalNanosecond
	cpuNanosecondUserDiff := nanosecondUserCpuactUsage - lastMetricsCpuUsageUserNanosecond
	cpuNanosecondSystemDiff := nanosecondSystemCpuactUsage - lastMetricsCpuUsageSystemNanosecond
	cpuNanosecondThrottledDiff := nanosecondThrottledNanosecond - lastMetricsCpuThrottledNanosecond
	metricsNanosecondTimeDiff := now - lastMetricsTimestamp
	var cpuUsageTotalPercentage float64 = 0.0
	var cpuUsageUserPercentage float64 = 0.0
	var cpuUsageSystemPercentage float64 = 0.0
	var cpuUsageThrottledPercentage float64 = 0.0
	if metricsNanosecondTimeDiff > 0 {
		cpuUsageTotalPercentage = float64(cpuNanosecondTotalDiff)*100.0/float64(metricsNanosecondTimeDiff)
		cpuUsageUserPercentage = float64(cpuNanosecondUserDiff)*100.0/float64(metricsNanosecondTimeDiff)
		cpuUsageSystemPercentage = float64(cpuNanosecondSystemDiff)*100.0/float64(metricsNanosecondTimeDiff)
		cpuUsageThrottledPercentage = float64(cpuNanosecondThrottledDiff)*100.0/float64(metricsNanosecondTimeDiff)
	}

	lastMetricsCpuUsageTotalNanosecond = nanosecondTotalCpuactUsage
	lastMetricsCpuUsageUserNanosecond = nanosecondUserCpuactUsage
	lastMetricsCpuUsageSystemNanosecond = nanosecondSystemCpuactUsage
	lastMetricsCpuThrottledNanosecond = nanosecondThrottledNanosecond
	lastMetricsTimestamp = now

	var cpuactUsageTotalSec float64 = float64(nanosecondTotalCpuactUsage) / 1e9
	var cpuactUsageUserSec float64 = float64(nanosecondUserCpuactUsage) / 1e9
	var cpuactUsageSystemSec float64 = float64(nanosecondSystemCpuactUsage) / 1e9
	var cpuactThrottledSec float64 = float64(nanosecondThrottledNanosecond) / 1e9

	workflow_cpu_usage_total_sec.WithLabelValues(username, workflowname).Set(cpuactUsageTotalSec)
	workflow_cpu_usage_total_percentage.WithLabelValues(username, workflowname).Set(cpuUsageTotalPercentage)
	workflow_cpu_usage_user_sec.WithLabelValues(username, workflowname).Set(cpuactUsageUserSec)
	workflow_cpu_usage_user_percentage.WithLabelValues(username, workflowname).Set(cpuUsageUserPercentage)
	workflow_cpu_usage_system_sec.WithLabelValues(username, workflowname).Set(cpuactUsageSystemSec)
	workflow_cpu_usage_system_percentage.WithLabelValues(username, workflowname).Set(cpuUsageSystemPercentage)
	workflow_cpu_throttled_sec.WithLabelValues(username, workflowname).Set(cpuactThrottledSec)
	workflow_cpu_throttled_percentage.WithLabelValues(username, workflowname).Set(cpuUsageThrottledPercentage)
	workflow_cpu_throttled_periods_total.WithLabelValues(username, workflowname).Set(numberThrottledPeriods)
	workflow_cpu_periods_total.WithLabelValues(username, workflowname).Set(numberPeriods)
	statString := fmt.Sprintf("cpu_sec_total,%.9f,cpu_sec_user,%.9f,cpu_sec_system,%.9f,cpu_sec_throttled,%.9f,cpu_perc_total,%.6f,cpu_perc_user,%.6f,cpu_perc_system,%.6f,cpu_perc_throttled,%.6f,cpu_periods_throttled,%.1f,cpu_periods_total,%.1f", 
		cpuactUsageTotalSec,
		cpuactUsageUserSec,
		cpuactUsageSystemSec,
		cpuactThrottledSec,
		cpuUsageTotalPercentage,
		cpuUsageUserPercentage,
		cpuUsageSystemPercentage,
		cpuUsageThrottledPercentage,
		numberThrottledPeriods,
		numberPeriods,
	)
	//fmt.Println("cpu", statString)
	return statString
}

func updateNetworkStats() string {
	netStats := make(map[string]uint64)
	err := containerstats.GetNetstatCounters(netStats)
	if err != nil {
		fmt.Println("Error getting netstat usage. Ignoring", err.Error())
		return ""
	}
	//PrettyPrint(netStats)
	// ListenDrops, ListenOverflows TCPBacklogDrop, TCPAbortOnMemory
	//fmt.Println(netStats["ListenDrops"], netStats["ListenOverflows"], netStats["TCPBacklogDrop"], netStats["TCPAbortOnMemory"])

	snmpStats := make(map[string]uint64)
	err = containerstats.GetSnmpCounters(snmpStats)
	if err != nil {
		fmt.Println("Error getting snmpStats usage")
		return ""
	}
	//PrettyPrint(snmpStats)
	// ActiveOpens PassiveOpens
	//fmt.Println(snmpStats["ActiveOpens"], snmpStats["PassiveOpens"])
	
	sockStats := make(map[string]uint64)
	err = containerstats.GetSockStats(sockStats)
	if err != nil {
		fmt.Println("Error getting sockstats")
		return ""
	}
	//PrettyPrint(sockStats)
	/*
	{
		"sockets_used": 910,
		"tcp_alloc": 537,
		"tcp_inuse": 81,
		"tcp_mem": 19,
		"tcp_orphan": 0,
		"tcp_tw": 153
	}
	*/

	workflow_net_tcpext_listen_drops_total.WithLabelValues(username, workflowname).Set(float64(netStats["ListenDrops"]))
	workflow_net_tcpext_listen_overflows_total.WithLabelValues(username, workflowname).Set(float64(netStats["ListenOverflows"]))
	workflow_net_tcp_backlog_drops_total.WithLabelValues(username, workflowname).Set(float64(netStats["TCPBacklogDrop"]))
	workflow_net_tcp_abort_on_memory_total.WithLabelValues(username, workflowname).Set(float64(netStats["TCPAbortOnMemory"]))
	workflow_net_tcp_active_opens_total.WithLabelValues(username, workflowname).Set(float64(snmpStats["ActiveOpens"]))
	workflow_net_tcp_passive_opens_total.WithLabelValues(username, workflowname).Set(float64(snmpStats["PassiveOpens"]))
	workflow_net_sockets_used_total.WithLabelValues(username, workflowname).Set(float64(sockStats["sockets_used"]))
	workflow_net_tcp_inuse_total.WithLabelValues(username, workflowname).Set(float64(sockStats["tcp_inuse"]))
	workflow_net_tcp_orphan_total.WithLabelValues(username, workflowname).Set(float64(sockStats["tcp_orphan"]))
	workflow_net_tcp_tw_total.WithLabelValues(username, workflowname).Set(float64(sockStats["tcp_tw"]))
	workflow_net_tcp_alloc_total.WithLabelValues(username, workflowname).Set(float64(sockStats["tcp_alloc"]))
	workflow_net_tcp_mem_total.WithLabelValues(username, workflowname).Set(float64(sockStats["tcp_mem"]))

	statString := fmt.Sprintf("net_listen_drops_total,%d,net_listen_overflows_total,%d,net_tcp_backlog_drops_total,%d,net_tcp_abort_on_memory_total,%d,net_tcp_active_opens_total,%d,net_tcp_passive_opens_total,%d,net_sockets_used,%d,net_tcp_inuse,%d,net_tcp_orphan,%d,net_tcp_tw,%d,net_tcp_alloc,%d,net_tcp_mem,%d", 
	netStats["ListenDrops"], 
	netStats["ListenOverflows"], 
	netStats["TCPBacklogDrop"], 
	netStats["TCPAbortOnMemory"],
	snmpStats["ActiveOpens"], 
	snmpStats["PassiveOpens"],
	sockStats["sockets_used"],
	sockStats["tcp_inuse"],
	sockStats["tcp_orphan"],
	sockStats["tcp_tw"],
	sockStats["tcp_alloc"],
	sockStats["tcp_mem"],
)
	return statString
}

func updateResourceStats() error {
	now := uint64(time.Now().UnixNano())

	memoryStatsString := updateMemoryStats()

	pidsStatsString := updatePidsStats()

	cpuStatsString := updateCpuStats()

	networkStatsString := updateNetworkStats()

	fmt.Printf("[resources],timestamp_sec,%.9f,%s,%s,%s,%s\n", 
		float64(now)/1e9,
		memoryStatsString, pidsStatsString, cpuStatsString, networkStatsString)

	return nil
}

func PrettyPrint(v interface{}) (err error) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err == nil {
			fmt.Println(string(b))
	}
	return
}

func inFlightRequestsCounter(inFlightRequestsCounterChan <-chan int) {
	for i := range inFlightRequestsCounterChan {
		if i == 1 {
			workflow_requests_started_count.WithLabelValues(username, workflowname).Inc()
			workflow_requests_in_flight_count.WithLabelValues(username, workflowname).Inc()
		} else if i == -1 {
			workflow_requests_finished_count.WithLabelValues(username, workflowname).Inc()
			workflow_requests_in_flight_count.WithLabelValues(username, workflowname).Dec()
		} else {

		}
	}
}
