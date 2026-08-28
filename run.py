import os
import sys
import traceback

# Save log directory
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_error.log")

try:
    # Switch working dir to script dir
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from PyQt6.QtWidgets import QApplication
    from src.main import MainWindow

    def main():
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()
except Exception as e:
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("ERR_EXCEPTION:\n")
        traceback.print_exc(file=f)
    sys.exit(1)
