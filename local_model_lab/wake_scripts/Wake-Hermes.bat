@echo off
title Wake Hermes PC (Wake-on-LAN)
echo [Hermes] Broadcasting Wake-on-LAN Magic Packet to 00:13:EF:60:04:42...
powershell -Command "$mac = '00:13:EF:60:04:42'.Replace(':','').Replace('-',''); $packet = [byte[]](,0xFF * 6) + (,([byte[]]($mac -split '(..)' | ? {$_} | %% { [Convert]::ToByte($_, 16) })) * 16); $client = New-Object System.Net.Sockets.UdpClient; $client.Connect('10.0.0.255', 9); $client.Send($packet, $packet.Length); $client.Close(); Write-Host 'Magic packet sent successfully!'"
powershell -Command "$mac = '04:42:1A:EA:BF:E7'.Replace(':','').Replace('-',''); $packet = [byte[]](,0xFF * 6) + (,([byte[]]($mac -split '(..)' | ? {$_} | %% { [Convert]::ToByte($_, 16) })) * 16); $client = New-Object System.Net.Sockets.UdpClient; $client.Connect('10.0.0.255', 9); $client.Send($packet, $packet.Length); $client.Close(); Write-Host 'Ethernet fallback packet sent!'"
echo.
echo Wake packet sent to Hermes Host PC. Wait ~10-15 seconds for boot.
pause
