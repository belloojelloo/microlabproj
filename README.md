# HIL FPGA ALSU GUI MVP

## What this project is

This project is a standalone GUI demo for the PC-side control app of a Hardware-in-the-Loop FPGA project.

It simulates connection, ALSU operation calculation, bitstream selection, fake upload progress, and result display locally.

It does not yet connect to a real Raspberry Pi or FPGA.

## Folder contents

- `pc_gui/` = actual GUI app
- `requirements_pc.txt` = Python dependencies
- `pi_server/` = placeholder for future Raspberry Pi code
- `scripts/` = placeholder/helper scripts
- `tests/` = placeholder tests

## Requirements

- Windows PC
- Python 3.10 or newer recommended
- Internet connection for first-time dependency installation

## Run from a zip file on Windows PowerShell

1. Extract the zip file to a folder on your PC.
2. Open PowerShell.
3. Change into the extracted project folder:

```powershell
cd "PATH_TO_EXTRACTED_FOLDER"
```

4. Create a virtual environment:

```powershell
python -m venv .venv
```

5. Upgrade `pip` inside the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

6. Install the required packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_pc.txt
```

7. Start the GUI:

```powershell
.\.venv\Scripts\python.exe -m pc_gui.main
```

## Alternative if you use the Python launcher

If `python` is not the correct command on your PC, you can create the virtual environment with:

```powershell
py -m venv .venv
```

You can then keep using:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements_pc.txt
.\.venv\Scripts\python.exe -m pc_gui.main
```

## If PowerShell blocks activation

You do not need to activate the virtual environment.

This project runs the virtual environment Python directly:

```powershell
.\.venv\Scripts\python.exe
```

So PowerShell execution policy issues with activation scripts should not block startup.

## How to test the GUI

After the app opens:

- IP: `localhost`
- Port: `5000`
- Click `Connect`
- Choose `ADD`
- Set `A = 10`
- Set `B = 5`
- Click `Send`

Expected result:

- Decimal: `15`
- Hex: `0x000F`
- Binary: `0b00001111`

## How to test upload

Create a dummy bitstream file in the project folder:

```powershell
.\.venv\Scripts\python.exe -c "open('test_dummy.bit','wb').write(b'1234')"
```

Then in the GUI:

- Click `Browse`
- Select `test_dummy.bit`
- Click `Upload & Program FPGA`
- Progress should reach `100%`
- Status should show `FPGA programmed successfully`

## Common issues

- `python` is not recognized:
  Install Python from [python.org](https://www.python.org/) and check `Add Python to PATH` during installation.
- `ModuleNotFoundError: customtkinter`:
  Run the install command again using the virtual environment Python path:
  `.\.venv\Scripts\python.exe -m pip install -r requirements_pc.txt`
- App does not open:
  Make sure you are inside the extracted project folder before running the startup command.
- File picker does not show `.bit`:
  Choose `All files` and select the file manually.

## Important note

This is a GUI-only MVP.

Real Raspberry Pi support, UART/SPI/I2C, FPGA programming, and hardware communication are future work.

## Demo checklist

Connect -> Send ADD -> Check result -> Browse `.bit` -> Upload -> Disconnect -> Close app
