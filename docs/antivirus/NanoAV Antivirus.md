# NanoAV Antivirus

 - **Installation method** \
download the free trial from https://www.nanoav.pro/getExe.php?type=exe
<br/>

- **Scan method** \
"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" scan "path/to/the/file"
<br/>

 - **How to get last update (command or script)**
```bash
"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" avinfo
```

    General information:
    Virus base: 0.14.47.25540 (2022-02-22 10:04:59)
    Antivirus engine: 1.0.146.91097 (2022-01-19 17:00:49)
    The time of the last full system scan: Never
    Real time protection state:
    File guard: Inactive
    Web guard: Inactive


<br/>

- **Update process** \
"C:\Program Files (x86)\NANO Antivirus\bin>nanoavcl.exe" update
<br/><br/>
 - **How to get expiration date (command or script)**
<br/><br/>

 - **How to validate license**
<br/><br/>


 - **How to reach the version**

Command-Line (Last Update Command)
```bash
"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" avinfo
```
Command-Line (Last Update Result)

    General information:  
    Virus base: 0.14.47.25540 (2022-02-22 10:04:59)  
    Antivirus engine: 1.0.146.91097 (2022-01-19 17:00:49)  
    The time of the last full system scan: Never  
    Real time protection state:  
    File guard: Inactive  
    Web guard: Inactive


<br/><br/>

- **Offline Update
(Make offline updates)  
(Use offline updates)**

It can create offline updates by doing the following:

**Make offline updates:**

01- make sure nano antivirus virus signature is update

02- run command:

**Command-Line (Make offline updates)**

```bash
@echo off
color 0A
title "NanoAV-update maker"
rmdir "D:\NanoAV-update\" /s /q
del "D:\NanoAV-update.zip"
mkdir "D:\NanoAV-update\"
"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" makeupdate "D:\NanoAV-update"
"C:\Program Files\WinRAR\Rar.exe" a -r "D:\NanoAV-update.zip" "D:\NanoAV-update"
pause
exit
```
03- The NanoAV-update.zip file is an offline antivirus update

**Use offline updates:**

Follow the steps below to update your antivirus offline:

01- Extract the offline update .zip file in a drive (like D:\)

02- Run the following command to update the antivirus as offline:

**Command-Line (Use offline updates)**
```bash
"C:\Program Files (x86)\NANO Antivirus\bin\nanoavcl.exe" update -source="D:\NanoAV-update"
````
03- Wait for the antivirus to update offline.
