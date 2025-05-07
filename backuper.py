import paramiko # type: ignore
from scp import SCPClient, SCPException # type: ignore
import os
import socket
from datetime import datetime
from dotenv import load_dotenv
from logger import server_log


class BackupManager:
    def __init__(self):
        try:
            load_dotenv()
            ubnt_username = os.getenv('UBNT_USERNAME')
            ubnt_passwords = os.getenv('UBNT_PASSWORDS', '').split()
            self.username = ubnt_username
            self.possible_passwords = ubnt_passwords
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
            self.backup_dir = os.path.join(self.script_dir, "backups")
            os.makedirs(self.backup_dir, exist_ok=True)
            server_log.info(f"BackupManager manager initialized")
        except Exception as e:
            server_log.info(f"Failed to initialize BackupManager: {str(e)}")
            exit(1)

    def _generate_filename(self, ip: str) -> str:
        """Generate filename in format: ip_YYYYMMDD_HHMMSS.cfg"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{ip}_{timestamp}.cfg"

    def backupUbnt(self, ip: str) -> None:
        """Perform backup for specified IP address"""
        server_log.debug(f"[{ip}] Staring backup ubnt device")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        successful = False
        last_exception = None
        
        for password in self.possible_passwords:
            try:
                # Attempt connection with current password
                ssh.connect(
                    ip,
                    username=self.username,
                    password=password,
                    timeout=10,
                    banner_timeout=20
                )
                
                # If connection successful
                successful = True
                break
                
            except paramiko.AuthenticationException:
                continue  # Try next password
                
            except (socket.timeout, socket.gaierror, paramiko.SSHException) as e:
                last_exception = f"[{ip}] Connection error: {str(e)}"
                break  # Stop trying passwords on connection error

            except Exception as e:
                server_log.warning(f"Unexpected error: {str(e)}")
                return f"Unexpected error: {str(e)}"

        if not successful:
            error_msg = last_exception if last_exception else "All passwords failed"
            server_log.warning(f"[{ip}] Backup failed: {error_msg}")
            backup_status = f"Backup failed: {error_msg}"
            return backup_status

        try:
            # Setup SCP transfer
            with SCPClient(ssh.get_transport()) as scp:
                filename = self._generate_filename(ip)
                filepath = os.path.join(self.backup_dir, filename)
                scp.get('/tmp/system.cfg', filepath)
                server_log.info(f"[{ip}] Backup successful: {filename}")
                backup_status = f"Backup successful: {filename}"
                
        except SCPException as e:
            server_log.warning(f"[{ip}] File transfer failed: {str(e)}")
            backup_status = f"File transfer failed: {str(e)}"
            
        except (FileNotFoundError, PermissionError) as e:
            server_log.warning(f"[{ip}] Local file error: {str(e)}")
            backup_status = f"Local file error: {str(e)}"
            
        except Exception as e:
            server_log.warning(f"[{ip}] Unexpected error: {str(e)}")
            backup_status = f"Unexpected error: {str(e)}"
            
        finally:
            ssh.close()
            return backup_status


backuper = BackupManager()