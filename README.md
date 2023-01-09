# KPI Automation Project

This repo contains a simple ETL script for the KPI Automation Project.

### Prerequisites

Python 3.6 or higher (created with 3.7.0) and pip. If you install the [latest version of Python for Windows](https://www.python.org/downloads/windows/) pip will already be included. In some Linux environments you may need to install pip separately (e.g. sudo apt install python3-pip), see [this guide](https://packaging.python.org/tutorials/installing-packages/#requirements-for-installing-packages) more information.

This script uses the following third-party libraries which can be installed with pip and the requirements.txt:
* [requests](https://docs.python-requests.org/en/master/): HTTP requests library
* [pandas](https://pandas.pydata.org/): data analysis library
* [dotenv](https://github.com/theskumar/python-dotenv) - Used to load the Salesforce API credentials into environment variables from a ".env" file not committed to this repository for security. This also handles differences in setting environment variables between Windows, Mac and Linux environments.

### Installing

1. It is recommended to [create a virtual environment](https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments) to avoid causing problems with any other python packages you may have installed. There are many ways to do this, the following is just one way. This command will create a virtual environment folder called "venv" in the current directory (in some Linux environments you might need to replace python with python3):

```
python -m venv venv
```

Activating the virtual environment will depend on your operating system or terminal environment. In most Linux environments:

```
source venv/bin/activate
```

In Windows PowerShell:

```
.\venv\Scripts\activate
```

2. Navigate to the folder containing requirements.txt and install with pip (in some Linux environments you may need to replace pip with pip3):

```
pip install -r requirements.txt
```

3. Create a plain text file with the file name ".env" (in Windows environments, ensure that no hidden file extension such as ".txt" has been added to the file). Add the following lines followed by the client_id, client_secret, username and password values for the Salesforce API user:

```
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
SALESFORCE_USERNAME=
SALESFORCE_PASSWORD=
```

4. Assuming no errors appeared in the previous step, you should now be able to run the script:

```
python etl.py
```

### Compiling

The Windows executable was created with [PyInstaller](https://www.pyinstaller.org/). If you want to create a new executable to share with others after modifying the script, install PyInstaller in your virtual environment (you will need to be in a Windows environment to create a Windows executable):

```
pip install pyinstaller
```

Then run this command:

```
pyinstaller -F etl.py
```

If successful the executable can be found in the dist folder. If not successful, you may need to follow [these steps](https://medium.com/@lironsoffer/pyinstaller-with-pandas-problems-solutions-and-workflow-with-code-examples-c72973e1e23f) to ensure the pandas modules are being found.