// +build linux

package containerstats

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ParseUint converts a string to an uint64 integer.
// Negative values are returned at zero as, due to kernel bugs,
// some of the memory cgroup stats can be negative.
func ParseUint(s string, base, bitSize int) (uint64, error) {
	value, err := strconv.ParseUint(s, base, bitSize)
	if err != nil {
		intValue, intErr := strconv.ParseInt(s, base, bitSize)
		// 1. Handle negative values greater than MinInt64 (and)
		// 2. Handle negative values lesser than MinInt64
		if intErr == nil && intValue < 0 {
			return 0, nil
		} else if intErr != nil && intErr.(*strconv.NumError).Err == strconv.ErrRange && intValue < 0 {
			return 0, nil
		}

		return value, err
	}

	return value, nil
}

// ParseKeyValue parses a space-separated "name value" kind of cgroup
// parameter and returns its key as a string, and its value as uint64
// (ParseUint is used to convert the value). For example,
// "io_service_bytes 1234" will be returned as "io_service_bytes", 1234.
func ParseKeyValue(t string) (string, uint64, error) {
	parts := strings.SplitN(t, " ", 3)
	if len(parts) != 2 {
		return "", 0, fmt.Errorf("line %q is not in key value format", t)
	}

	value, err := ParseUint(parts[1], 10, 64)
	if err != nil {
		return "", 0, fmt.Errorf("unable to convert to uint64: %v", err)
	}

	return parts[0], value, nil
}

func ParseCpuUsageLine(t string) (uint64, uint64, error) {
	//fmt.Println("ParseCpuUsageLine",t)
	parts := strings.SplitN(t, " ", -1)
	//fmt.Println("ParseCpuUsageLine",parts,len(parts))
	if len(parts) != 3 {
		return 0, 0, fmt.Errorf("line %q is not in 3 uint64 format", t)
	}

	valueUser, err := ParseUint(parts[1], 10, 64)
	if err != nil {
		return 0, 0, fmt.Errorf("unable to convert user cpu usage to uint64: %v", err)
	}

	valueSystem, err := ParseUint(parts[2], 10, 64)
	if err != nil {
		return 0, 0, fmt.Errorf("unable to convert system cpu usage to uint64: %v", err)
	}

	return valueUser, valueSystem, nil
}


func ParseKeyValueLines(keyline string, valueline string, stats map[string]uint64) (error) {
	//fmt.Println("ParseNetstatKeyValueLines",keyline)
	//fmt.Println("ParseNetstatKeyValueLines",valueline)
	keyparts := strings.SplitN(keyline, " ", -1)
	//fmt.Println("ParseNetstatKeyValueLines",len(keyparts),keyparts)
	if len(keyparts) < 2 {
		return fmt.Errorf("line %q is not a keyline format", keyline)
	}

	valueparts := strings.SplitN(valueline, " ", -1)
	//fmt.Println("ParseNetstatKeyValueLines",len(valueparts),valueparts)
	if len(valueparts) < 2 || len(valueparts) != len(keyparts) {
		return fmt.Errorf("line %q is not a keyline format", valueline)
	}

	for i:=1; i<len(keyparts); i++ {
		value, err := ParseUint(valueparts[i], 10, 64)
		if err != nil {
			continue
		}
		stats[keyparts[i]] = value
	}

	return nil
}


func ParseSingleKeyValueLine(keyvalueline string, stats map[string]uint64) (error) {
	//fmt.Println("ParseSingleKeyValueLine", keyvalueline)
	sanitized_keyvalueline := strings.ToLower(strings.ReplaceAll(keyvalueline, ":", ""))
	//fmt.Println("ParseSingleKeyValueLine", sanitized_keyvalueline)
	keyvalparts := strings.SplitN(sanitized_keyvalueline, " ", -1)
	//fmt.Println("ParseNetstatKeyValueLines",len(keyvalparts),keyvalparts)
	if len(keyvalparts) < 3 {
		return fmt.Errorf("line %q is not a keyvalueline format", sanitized_keyvalueline)
	}

	key_prefix := keyvalparts[0]
	for i := 1; i<len(keyvalparts); i+=2 {
		key_suffix := keyvalparts[i]
		value, err := ParseUint(keyvalparts[i+1], 10, 64)
		if err != nil {
			continue
		}
		stats[key_prefix + "_" + key_suffix] = value
	}
	return nil
}


// OpenFile opens a cgroup file in a given dir with given flags.
func OpenFile(file string) (*os.File, error) {
	if file == "" {
		return nil, fmt.Errorf("no file specified for %s", file)
	}
	fd, err := os.Open(file)
	return fd, err
}


// ReadFile reads data from a cgroup file in dir.
// It is supposed to be used for cgroup files only.
func ReadFile(file string) (string, error) {
	fd, err := OpenFile(file)
	if err != nil {
		return "", err
	}
	defer fd.Close()
	var buf bytes.Buffer

	_, err = buf.ReadFrom(fd)
	return buf.String(), err
}


func GetMemoryStats(stats map[string]uint64) error {
	// Set stats from memory.stat.
	statsFile, err := OpenFile("/sys/fs/cgroup/memory/memory.stat")
	if err != nil {
		return err
	}
	defer statsFile.Close()

	sc := bufio.NewScanner(statsFile)
	for sc.Scan() {
		t, v, err := ParseKeyValue(sc.Text())
		if err != nil {
			return fmt.Errorf("failed to parse memory.stat (%q) - %v", sc.Text(), err)
		}
		stats[t] = v
	}
	return nil
}

func GetNumberOfProcesses(numberOfProcesses *uint64) error {
	// if the controller is not enabled, let's read PIDS from cgroups.procs
	// (or threads if cgroup.threads is enabled)
	contents, err := ReadFile("/sys/fs/cgroup/cpu/cgroup.procs")
	if err != nil {
		return err
	}
	pids := strings.Count(contents, "\n")
	*numberOfProcesses = uint64(pids)
	return nil
}

func GetCpuactUsageNanoseconds(nanosecondsCpuactUsage *uint64) error {
	// if the controller is not enabled, let's read PIDS from cgroups.procs
	// (or threads if cgroup.threads is enabled)
	contents, err := ReadFile("/sys/fs/cgroup/cpu/cpuacct.usage")
	if err != nil {
		return err
	}
	value, err := ParseUint(strings.TrimRight(contents, "\n"), 10, 64)
	if err != nil {
		return fmt.Errorf("unable to convert to uint64: %v", err)
	}
	*nanosecondsCpuactUsage = uint64(value)
	return nil
}


func GetSplitCpuactUsageNanoseconds(nanosecondUserCpuactUsage *uint64, 
		nanosecondSystemCpuactUsage *uint64, nanosecondTotalCpuactUsage *uint64) error {
	statsFile, err := OpenFile("/sys/fs/cgroup/cpu/cpuacct.usage_all")
	if err != nil {
		return err
	}
	defer statsFile.Close()

	sc := bufio.NewScanner(statsFile)
	for sc.Scan() {
		cpuUsageLine := sc.Text()
		if strings.Contains(cpuUsageLine, "cpu") {
			continue
		}
		userUsage, systemUsage, err := ParseCpuUsageLine(sc.Text())
		if err != nil {
			return fmt.Errorf("failed to parse memory.stat (%q) - %v", sc.Text(), err)
		}
		*nanosecondUserCpuactUsage = userUsage
		*nanosecondSystemCpuactUsage = systemUsage
		*nanosecondTotalCpuactUsage = userUsage + systemUsage
	}
	return nil
}


func GetCpuThrottlingStats(stats map[string]uint64) error {
	// Set stats from cpu.stat.
	statsFile, err := OpenFile("/sys/fs/cgroup/cpu/cpu.stat")
	if err != nil {
		return err
	}
	defer statsFile.Close()

	sc := bufio.NewScanner(statsFile)
	for sc.Scan() {
		t, v, err := ParseKeyValue(sc.Text())
		if err != nil {
			return fmt.Errorf("failed to parse cpu.stat (%q) - %v", sc.Text(), err)
		}
		stats[t] = v
	}
	return nil
}

func GetCountersFromKeyValueLines(filename string, filter string, stats map[string]uint64) error {
	keyValueLinesFile, err := OpenFile(filename)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	defer keyValueLinesFile.Close()

	sc := bufio.NewScanner(keyValueLinesFile)
	for sc.Scan() {
		keyLine := sc.Text()
		if !sc.Scan() {
			return fmt.Errorf("Unable to parse file.", filename, "Value line is missing")
		}
		valueLine := sc.Text()
		if strings.Contains(keyLine, filter) && strings.Contains(valueLine, filter) {
			err = ParseKeyValueLines(keyLine, valueLine, stats)
		}
	}
	return nil
}


func GetNetstatCounters(stats map[string]uint64) error {
	return GetCountersFromKeyValueLines("/proc/net/netstat", "TcpExt", stats)
}

func GetSnmpCounters(stats map[string]uint64) error {
	return GetCountersFromKeyValueLines("/proc/net/snmp", "Tcp", stats)
}

func GetSockStats(stats map[string]uint64) error {
	// Set stats from sockstat.
	socksFile, err := OpenFile("/proc/net/sockstat")
	if err != nil {
		return err
	}
	defer socksFile.Close()

	sc := bufio.NewScanner(socksFile)
	for sc.Scan() {
		keyvalueline := sc.Text()
		if strings.Contains(keyvalueline, "TCP") || strings.Contains(keyvalueline, "sockets") {
			err := ParseSingleKeyValueLine(sc.Text(), stats)
			if err != nil {
				return fmt.Errorf("failed to parsesockstats (%q) - %v", sc.Text(), err)
			}
		}
	}
	return nil
}