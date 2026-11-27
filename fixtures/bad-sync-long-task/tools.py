def run_shell(cmd: str):
    import subprocess
    return subprocess.run(cmd, shell=True, capture_output=True)
