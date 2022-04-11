# Disable Windows Defender Firewall using Group Policy (gpedit.msc)

01-Open Start.\
02-Search for **gpedit.msc** and click the top result to launch the Local Group Policy Editor.\
03-Navigate to the following path:

> Computer Configuration > Administrative Templates > Network > Network
> Connections > Windows Defender Firewall > Domain Profile

04-Double-click the **Windows Defender Firewall: Protect All Network Connections** on the right side.\
05-Check the **Disabled** option to turn off Windows 10 Windows Defender Firewall permanently.\
06-Navigate to the following path:

> Computer Configuration > Administrative Templates > Network > Network
> Connections > Windows Defender Firewall > Standard Profile

07-Double-click the **Windows Defender Firewall: Protect All Network Connections** on the right side.\
08-Check the **Disabled** option to turn off Windows 10 Windows Defender Firewall permanently.\
09-Click the **Apply** button.\
10-Click the **OK** button.
