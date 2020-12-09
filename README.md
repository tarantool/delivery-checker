# Delivery Checker

This is a program that downloads Tarantool's installation commands
and tries to run them on different OS.

## How to run

1. Install Python 3.6 or higher
2. Install Docker or/and VirtualBox
2. Change `config.json` if necessary
3. Run `check.py`

## Config with all available options

```json
{
***REMOVED***
  "commands_url": "https://www.tarantool.io/api/tarantool/info/versions/",
  "send_to_remote": {
    "login": "centos",
    "password": "centos",
    "host": "123.456.789.012",
    "archive": "server_name",
    "remote_dir": "/opt/delivery_checker/remote"
  },
  "use_remote_results": false,
  "os_params": {
    "example_os": {
      "docker": {
        "image": "name_of_docker_image",
        "versions": [
          "2020",
          "latest"
        ],
        "skip": [
          "name_of_build_1",
          "name_of_build_2"
        ],
        "use_cache": false
      },
      "virtual_box": {
        "Name of VirtualBox VM": {
          "login": "root",
          "password": "toor",
          "host": "127.0.0.1",
          "port": 22,
          "remote_dir": "/opt/tarantool",
          "skip_prepare": false,
          "prepare_timeout": 360,
          "run_timeout": 60,
          "skip": [
            "name_of_build_1",
            "name_of_build_2"
          ]
        },
        "example_os_vm": {}
      }
    }
  }
}
```

## Example of output

In this case, the process finished with exit code 1 
because there are some errors.

```
OS: freebsd_12.2. Build: pkg_2.4. Elapsed time: 95.85. OK
OS: freebsd_12.2. Build: ports_2.4. Elapsed time: 355.99. TIMEOUT
OS: amazon-linux_2. Build: script_2.5. Elapsed time: 85.43. ERROR
OS: amazon-linux_2. Build: script_1.10. Elapsed time: 88.83. ERROR
OS: os-x_10.12. Build: 2.5. SKIP
OS: os-x_10.12. Build: 2.6. Elapsed time: 521.86. OK
OS: docker-hub_2.5. Build: 2.5. Elapsed time: 122.72. OK
```
