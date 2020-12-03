import time


def wait_until(func, excepted=None, timeout=30, period=1, error_msg='Impossible to wait', log=print, *args, **kwargs):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if func(*args, **kwargs) == excepted:
                return True
        except Exception as e:
            log(f'{error_msg}: {e}')
        time.sleep(period)

    log(f'{error_msg}: timeout')
    return False


def print_logs(in_data=None, out_data=None, log=print, in_prefix='< ', out_prefix='> '):
    if in_data:
        for line in in_data.splitlines():
            if line:
                log(f'{in_prefix}{line}')

    if out_data:
        for line in out_data.splitlines():
            if line:
                log(f'{out_prefix}{line}')
        log('')
