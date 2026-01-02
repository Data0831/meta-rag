class ANSIColor:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


def _print_base(text, color_code, bold=False, end="\n"):
    """內部輔助函數：處理 ANSI 格式拼接"""
    prefix = ANSIColor.BOLD + color_code if bold else color_code
    print(f"{prefix}{text}{ANSIColor.RESET}", end=end)


# 快捷接口
def print_red(text, bold=False, end="\n"):
    _print_base(text, ANSIColor.RED, bold, end)


def print_green(text, bold=False, end="\n"):
    _print_base(text, ANSIColor.GREEN, bold, end)


def print_yellow(text, bold=False, end="\n"):
    _print_base(text, ANSIColor.YELLOW, bold, end)


def print_blue(text, bold=False, end="\n"):
    _print_base(text, ANSIColor.BLUE, bold, end)


def print_cyan(text, bold=False, end="\n"):
    _print_base(text, ANSIColor.CYAN, bold, end)
