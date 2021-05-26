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
		if os.IsNotExist(err) {
			return nil
		}
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
		fmt.Errorf("unable to convert to uint64: %v", err)
	}
	*nanosecondsCpuactUsage = uint64(value)
	return nil
}
