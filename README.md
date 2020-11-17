# Delivery Checker

This is a program that downloads Tarantool's installation commands
and tries to run them on different OS.

## How to run

1. Install Python 3.6 or higher
2. Install Docker or/and VirtualBox
2. Change `config.json` if necessary
3. Run `main.py`

## Example of config

```json
{
  "commands_url": "https://www.tarantool.io/api/tarantool/info/versions/",
  "send_to_remote": {
    "credentials": {
      "login": "centos",
      "password": "centos",
      "host": "123.456.789.012"
    },
    "archive": "server_name",
    "remote_dir": "/opt/delivery_checker/remote"
  },
  "load_remote_cache": false,
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
        ]
      },
      "virtual_box": {
        "Name of VirtualBox VM without '_base' suffix": {
          "credentials": {
            "login": "root",
            "password": "toor",
            "host": "127.0.0.1",
            "port": 22
          },
          "remote_dir": "/opt/tarantool",
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
OS: fedora_31. Build: script_2.5. OK
OS: fedora_31. Build: script_1.10. OK
OS: fedora_31. Build: nightly_2.5. TIMEOUT
OS: fedora_31. Build: beta_2.6. OK
OS: fedora_31. Build: manual_2.5. TIMEOUT
OS: fedora_31. Build: manual_1.10. OK
OS: freebsd_12.2. Build: pkg_2.4. SKIP
OS: freebsd_12.2. Build: ports_2.4. SKIP
OS: amazon-linux_1. Build: script_2.5. ERROR
OS: amazon-linux_2. Build: script_2.5. ERROR
OS: docker_2.4. Build: 2.4. OK
```
