# zabbix-zfs

Zabbix template & script to monitor ZFS on Linux.

Single Python script that emits all information needed for discovery & data gathering in a single JSON.
All items are defined as `Dependent` and extract relevant data using JSONPath queries.

<details>
    <summary>Click to expand JSON example</summary>

```json
{
  "vdevs": {
    "/dev/sda1": {
      "name": "/dev/sda1",
      "size": 0,
      "alloc": 0,
      "free": 0,
      "frag": 0,
      "usage": 0,
      "online": 1,
      "errors": {
        "read": 0,
        "write": 0,
        "cksum": 0
      }
    }
  },

  "pools": {
    "pool1": {
      "name": "pool1",
      "size": 11957188952064,
      "alloc": 4227267283968,
      "free": 7729921668096,
      "frag": 5,
      "usage": 35,
      "dedup": 1.0,
      "scrub": 0,
      "online": 1
    }
  },

  "datasets": {
    "pool1": {
      "name": "pool1",
      "avail": 5502826989670,
      "used": 3162194032538,
      "compress": 1.05,
      "referenced": 38300
    }
  },

  "arc": {
    "l1": {
      "size": 5398891600,
      "hitrate": 91.56803867935483,
      "free": 458843264
    },
    "l2": {
      "usage": 142278352384,
      "usage_actual": 137375770112,
      "hitrate": 94.00152633863829,
      "bytes_read": 241515501568,
      "bytes_written": 25932241920,
      "io_error": 0,
      "cksum_bad": 0
    }
  },

  "slab": 291337024
}
```

</details>

## Features

- Low level discovery of:
  - Pools
  - Datasets
  - Devices
  - L2ARC - items will be created only if it's present
- Items:
  - Pools: health, disk usage, fragmentation, deduplication, scrub
  - Datasets: disk usage, compression ratio
  - Devices: health, disk usage, error counts, fragmentation
  - SLAB usage
  - L1 & L2 ARC stats
- Triggers:
  - Pool & device health
  - Pool & dataset disk usage
  - High fragmentation
  - ARC usage
  - L2ARC errors & low hit rate
  - Scrub
- Zabbix agent passive checks. Can be converted to active if needed.

## Macros

- `{$ZFS_DS_EXCLUDE}` - Regexp to exclude the datasets during discovery
- `{$ZFS_DS_INCLUDE}` - Regexp to include the datasets during discovery
- `{$ZFS_DS_USAGE_CRIT}` - Dataset usage in % when crit alert is triggered
- `{$ZFS_DS_USAGE_HIGH}` - Dataset usage in % when high alert is triggered
- `{$ZFS_POOL_EXCLUDE}` - Regexp to exclude the pools during discovery
- `{$ZFS_POOL_INCLUDE}` - Regexp to include the pools during discovery
- `{$ZFS_POOL_FRAG_HIGH}` - Pool fragmentation in % when high alert is triggered
- `{$ZFS_POOL_USAGE_CRIT}` - Pool usage in % when crit alert is triggered
- `{$ZFS_POOL_USAGE_HIGH}` - Pool usage in % when high alert is triggered
- `{$ZFS_VDEV_ERROR_THRESHOLD}` - vdev and L2ARC error threshold when triggers fire
- `{$ZFS_VDEV_EXCLUDE}` - Regexp to exclude the vdevs during discovery
- `{$ZFS_VDEV_INCLUDE}` - Regexp to include the vdevs during discovery
- `{$ZFS_ARC_META_THRESHOLD}` - Alert when ARC meta usage % goes over this value
- `{$ZFS_L2ARC_ERROR_THRESHOLD}` - Error threshold for L2ARC errors
- `{$ZFS_L2ARC_HITRATE_THRESHOLD}` - Alert when L2ARC hit rate falls below this value

## Requirements

- Tested on OpenZFS 2.x, maybe will work with 0.8.x
- Tested on Zabbix 5.0, but should work on 4.2+
- Python3

## Installation

- Place `zfs.conf` in `/etc/zabbix/zabbix_agentd.d`
- Place `zfs.py` in `/etc/zabbix/scripts`
  You can put it into any other place, but then you'll have to adjust `zfs.conf`
- Restart `zabbix-agentd`
- Import `template_zfs.xml`
- You're good to go
