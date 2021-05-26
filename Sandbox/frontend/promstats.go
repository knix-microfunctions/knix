package main

import (
	"log"
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
var lastMetricsCpuUsageNanosecond uint64

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

var workflow_cpu_usage_sec = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_sec",
	Help: "The total CPU time in seconds for all processes inside a knix sandbox",
    },
	[]string{"knix_user", "knix_workflow",})

var workflow_cpu_usage_percentage = promauto.NewGaugeVec(prometheus.GaugeOpts{
	Name: "knix_workflow_cpu_usage_percentage",
	Help: "The total usage CPU in percentage for all processes inside a knix sandbox",
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

func updateResourceStats() error {
	memoryStats := make(map[string]uint64)
	var err = containerstats.GetMemoryStats(memoryStats)
	if err != nil {
		log.Println("Error getting memory stats")
		return err
	}
	var ( 
		total_rss = float64(memoryStats["total_rss"])/(1024.0*1024.0)
		total_cache = float64(memoryStats["total_cache"])/(1024.0*1024.0)
		total_mapped_file = float64(memoryStats["total_mapped_file"])/(1024.0*1024.0)
	)
	//fmt.Println("memory", total_rss, total_cache, total_mapped_file)
	workflow_memory_rss_mb.WithLabelValues(username, workflowname).Set(total_rss)
	workflow_memory_cache_mb.WithLabelValues(username, workflowname).Set(total_cache)
	workflow_memory_mapped_file_mb.WithLabelValues(username, workflowname).Set(total_mapped_file)

	var numberOfProcesses uint64
	err = containerstats.GetNumberOfProcesses(&numberOfProcesses)
	if err != nil {
		log.Println("Error getting number of pids")
		return err
	}
	workflow_process_count.WithLabelValues(username, workflowname).Set(float64(numberOfProcesses))
	//fmt.Println("pids", numberOfProcesses)

	var cpuactUsageNs uint64
	err = containerstats.GetCpuactUsageNanoseconds(&cpuactUsageNs)
	if err != nil {
		log.Println("Error getting cpu usage")
		return err
	}
	now := uint64(time.Now().UnixNano())

	if lastMetricsCpuUsageNanosecond == 0 || lastMetricsTimestamp == 0 {
		lastMetricsCpuUsageNanosecond = cpuactUsageNs
		lastMetricsTimestamp = now
	}

	cpuNanosecondDiff := cpuactUsageNs - lastMetricsCpuUsageNanosecond
	metricsNanosecondTimeDiff := now - lastMetricsTimestamp
	var cpuUsagePercentage float64 = 0.0
	if metricsNanosecondTimeDiff > 0 {
		cpuUsagePercentage = float64(cpuNanosecondDiff)*100.0/float64(metricsNanosecondTimeDiff)
	}

	lastMetricsCpuUsageNanosecond = cpuactUsageNs
	lastMetricsTimestamp = now


	var cpuactUsageSec float64 = float64(cpuactUsageNs) / 1e9
	workflow_cpu_usage_sec.WithLabelValues(username, workflowname).Set(cpuactUsageSec)
	workflow_cpu_usage_percentage.WithLabelValues(username, workflowname).Set(cpuUsagePercentage)
	//fmt.Println("cpu", cpuactUsageSec)

	
	log.Printf("resources,timestamp_sec,%.9f,memory_rss_mb,%.6f,memory_cache_mb,%.6f,memory_mapped_file_mb,%.6f,pids,%d,cpu_sec,%.9f,cpu_perc,%.6f\n", float64(now)/1e9,total_rss, total_cache,total_mapped_file,numberOfProcesses,cpuactUsageSec,cpuUsagePercentage)
	//fmt.Println("resources", "timestamp", float64(now.UnixNano())/1e6, "memory", total_rss, total_cache, total_mapped_file, "pids", numberOfProcesses, "cpu", cpuactUsageSec)

	return nil
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
