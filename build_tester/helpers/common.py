import os
import time


def get_best_prepare_script(prepare_dir_path, set_1, set_2=None):
    set_2 = set_2 or set()

    best_script_score = 1
    best_script_name = None

    def name_score(name):
        name = set(os.path.splitext(name)[0].split('_'))
        return max(
            len(name & set_1) * 2 + 1 if name.issubset(set_1) else 0,
            len(name & set_2) * 2 if name.issubset(set_2) else 0,
        )

    for script_name in sorted(os.listdir(prepare_dir_path)):
        score = name_score(script_name)
        if score > best_script_score:
            best_script_score = score
            best_script_name = os.path.join(prepare_dir_path, script_name)

    return best_script_name


def wait_until(func, excepted=None, timeout=30, period=1, error_msg='Impossible to wait', log=print, *args, **kwargs):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if func(*args, **kwargs) == excepted:
                return True
        except Exception as e:
            log(f'{error_msg}: {e}\n')
        time.sleep(period)

    log(f'{error_msg}: timeout\n')
    return False


def get_header_str(name):
    return '\n'.join([
        '=' * 80,
        name,
        '=' * 80,
        ''
    ])


def get_subheader_str(name):
    return '\n'.join([
        '-' * 80,
        name,
        '-' * 80,
        ''
    ])


def get_title_str(name):
    return f'[{name}]: '


def get_lines_with_title(name, data, with_new_line=True):
    if len(str(data).strip()) == 0:
        return None

    new_line = '\n' if with_new_line else ''
    return f'{get_title_str(name)}{new_line}{data}'


def print_logs(in_data=None, out_data=None, log=print, in_prefix='COMMAND', out_prefix=''):
    if in_data:
        in_data = in_data.splitlines()
        if len(in_data) == 1:
            log(get_subheader_str(f'{in_prefix}: {in_data[0]}'))
        else:
            log(get_subheader_str(in_prefix))
            for line in in_data:
                if line:
                    log(f'{in_prefix}{line}')

    if out_data:
        lines = out_data.splitlines()
        for line in lines:
            if line:
                log(f'{out_prefix}{line}')
        if lines:
            log('')
