#!/usr/bin/env python3
import re
import json
import os
from subprocess import check_output, DEVNULL

# Constants
ZPOOL_CMD = '/sbin/zpool'  # ZFS pool command
ZFS_CMD = '/sbin/zfs'  # ZFS command
PROC_SPL_KMEM_SLAB = '/proc/spl/kmem/slab'  # Path to slab file
PROC_SPL_KSTAT_ZFS_ARCSTATS = '/proc/spl/kstat/zfs/arcstats'  # Path to ARC stats file

def safe_int(value, default=0):
    # Converts a value to an integer. If conversion fails, returns the default value.
    try:
        return int(value)
    except ValueError:
        return default

def safe_float(value, default=0.0):
    # Converts a value to a float. If conversion fails, returns the default value.
    try:
        return float(value)
    except ValueError:
        return default

def device_exists(path):
    # Checks if a device exists at the given path.
    return os.path.exists(path)

def run(cmd, split=r'\t'):
    # Runs a command and returns a list of lines, stripped and split by the given regex.
    try:
        r = check_output(
            cmd,
            encoding='utf8',
            stderr=DEVNULL
        )
        return [re.split(split, x.strip()) for x in r.split('\n') if x.strip()]
    except Exception as e:
        print(json.dumps({"error": f"Command failed: {e}"}))
        raise

def read_file(fn, skip=2, split=r'\s+'):
    # Reads a file, skips the specified number of lines, and splits lines by the given regex.
    try:
        with open(fn) as f:
            for i in range(skip):
                f.readline()
            return [re.split(split, x) for x in f.readlines()]
    except Exception as e:
        print(json.dumps({"error": f"Failed to read file {fn}: {e}"}))
        return []

def pool_io_stats(pool):
    # Reads IO statistics for a given ZFS pool.
    try:
        r = read_file(f'/proc/spl/kstat/zfs/{pool}/iostats', skip=1)
    except FileNotFoundError:
        r = read_file(f'/proc/spl/kstat/zfs/{pool}/io', skip=1)
    return {x[0]: safe_int(x[1]) for x in zip(r[0], r[1]) if x[1].isdigit()}

def state2int(state_str):
    # Converts a string state to an integer value.
    if state_str in ('ONLINE', 'AVAIL', 'INUSE'):
        return 1  # All good
    elif state_str == 'DEGRADED':
        return 2  # Degraded performance
    elif state_str in ('FAULTED', 'UNAVAIL', 'REMOVED', 'OFFLINE'):
        return 3  # Critical state
    else:
        return 0  # Unknown state

def pool_list(scrub, resilver):
    # Returns a list of pools with their stats.
    r = run([
        ZPOOL_CMD,
        "list",
        "-Hpo",
        "name,size,allocated,free,fragmentation,capacity,dedupratio,health"
    ])
    return {x[0]: {
        'name': x[0],
        'size': safe_int(x[1]),
        'alloc': safe_int(x[2]),
        'free': safe_int(x[3]),
        'frag': safe_int(x[4]),
        'usage': safe_int(x[5]),
        'dedup': safe_float(x[6]),
        'scrub': int(scrub[x[0]]),
        'resilver': int(resilver[x[0]]),
        'online': state2int(x[7]),
        'io': pool_io_stats(x[0]),
    } for x in r}

def pool_status():
    # Retrieves the status of ZFS pools, including scrub and resilver states, and vdev errors.
    r = run([
        ZPOOL_CMD,
        "status",
        "-Pp",
    ], split=r'\s+')
    pool = ""
    scrub = {}
    resilver = {}
    for l in r:
        if l[0] == "pool:":
            pool = l[1]
            scrub[pool] = False
            resilver[pool] = False
        elif l[0] == "scan:" and ' '.join(l[1:4]) == "scrub in progress":
            scrub[pool] = True
        elif l[0] == "scan:" and ' '.join(l[1:4]) == "resilver in progress":
            resilver[pool] = True
    vdev_errors = {}
    for x in r:
        if len(x) < 2 or not x[0].startswith('/'):
            continue
        try:
            vdev_errors[x[0]] = {
                'read': safe_int(x[2]),
                'write': safe_int(x[3]),
                'cksum': safe_int(x[4]),
            }
        except Exception:
            vdev_errors[x[0]] = {
                'read': 0,
                'write': 0,
                'cksum': 0,
            }
    return scrub, resilver, vdev_errors

def vdev_list(errors):
    # Returns a list of vdevs with their stats.
    r = run([
        ZPOOL_CMD,
        "list",
        "-PHvp",
    ])
    return {x[0]: {
        'name': x[0],
        'size': safe_int(x[1]),
        'alloc': safe_int(x[2]),
        'free': safe_int(x[3]),
        'frag': safe_int(x[6]),
        'usage': safe_int(x[7]),
        'online': state2int(x[9]),
        'errors': errors.get(x[0], {'read': 0, 'write': 0, 'cksum': 0}),
    } for x in r if x[0].startswith('/') and device_exists(x[0])}

def zfs_list():
    # Returns a list of ZFS datasets with their stats.
    r = run([
        ZFS_CMD,
        "list",
        "-Hpo",
        "name,avail,used,compressratio,referenced"
    ])
    return {x[0]: {
        'name': x[0],
        'avail': safe_int(x[1]),
        'used': safe_int(x[2]),
        'compress': safe_float(x[3]),
        'referenced': safe_int(x[4])
    } for x in r}

def slab_usage():
    # Calculates the total slab usage from /proc/spl/kmem/slab.
    return sum([safe_int(x[2]) for x in read_file(PROC_SPL_KMEM_SLAB) if x[2].isdigit()])

def arc_stats():
    # Retrieves ARC (Adaptive Replacement Cache) statistics.
    try:
        r = {x[0]: safe_int(x[2]) for x in read_file(PROC_SPL_KSTAT_ZFS_ARCSTATS)}
        l1 = r['hits'] + r['misses']
        l2 = r['l2_hits'] + r['l2_misses']
        return {
            'l1': {
                'size': r['size'],
                'hitrate': r['hits'] / l1 * 100 if l1 else 0,
                'free': r['memory_available_bytes'],
                'meta_used': r['arc_meta_used'],
            },
            'l2': {
                'usage': r['l2_size'],
                'usage_actual': r['l2_asize'],
                'hitrate': r['l2_hits'] / l2 * 100 if l2 else 0,
                'bytes_read': r['l2_read_bytes'],
                'bytes_written': r['l2_write_bytes'],
                'io_error': r['l2_io_error'],
                'cksum_bad': r['l2_cksum_bad'],
            }
        }
    except Exception as e:
        print(json.dumps({"error": f"Error in arc_stats: {e}"}))
        return {}

# Main execution
try:
    scrub, resilver, vdev_errors = pool_status()
    result = {
        'vdevs': vdev_list(vdev_errors),
        'pools': pool_list(scrub, resilver),
        'datasets': zfs_list(),
        'arc': arc_stats(),
        'slab': slab_usage(),
    }

    print(json.dumps(result, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
