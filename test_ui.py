from terminal_ui import TerminalUI
import time

ui = TerminalUI()

ui.start("Connecting...")
time.sleep(3)

ui.update("Resolving URL...")
time.sleep(3)

ui.update("Preparing Download...")
time.sleep(3)

ui.stop("Ready!")
