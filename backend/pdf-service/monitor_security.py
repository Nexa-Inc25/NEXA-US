#!/usr/bin/env python3
"""
NEXA Security Monitoring Dashboard
Real-time security monitoring and alerting
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import requests
from collections import defaultdict
from typing import Dict, List

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://nexa_db_94sr_user:H9AZevmgdNd5pWEFVkTm880HX5A6ATzd@dpg-d3mifuili9vc73a8a9kg-a.oregon-postgres.render.com/nexa_db_94sr")
API_URL = os.getenv("API_URL", "https://nexa-api-xpu3.onrender.com")
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK")  # Slack/Discord webhook for alerts

# Fix postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

class SecurityMonitor:
    """Security monitoring system"""
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.alerts = []
        self.metrics = defaultdict(int)
    
    def check_failed_logins(self, threshold: int = 5) -> List[Dict]:
        """Check for excessive failed login attempts"""
        
        sql = """
            SELECT username, failed_attempts, last_login, locked_until
            FROM users
            WHERE failed_attempts > :threshold
            ORDER BY failed_attempts DESC
        """
        
        with self.engine.connect() as conn:
            results = conn.execute(text(sql), {'threshold': threshold}).fetchall()
        
        alerts = []
        for row in results:
            alert = {
                'level': 'HIGH',
                'type': 'FAILED_LOGINS',
                'user': row[0],
                'attempts': row[1],
                'last_login': str(row[2]) if row[2] else 'Never',
                'locked': row[3] is not None
            }
            alerts.append(alert)
            print(f"⚠️ High failed logins: {row[0]} ({row[1]} attempts)")
        
        return alerts
    
    def check_suspicious_activity(self) -> List[Dict]:
        """Check audit logs for suspicious patterns"""
        
        sql = """
            SELECT username, action, COUNT(*) as count, 
                   array_agg(DISTINCT ip_address) as ips
            FROM audit_logs
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY username, action
            HAVING COUNT(*) > 50
            ORDER BY count DESC
        """
        
        with self.engine.connect() as conn:
            results = conn.execute(text(sql)).fetchall()
        
        alerts = []
        for row in results:
            if len(row[3]) > 3:  # Multiple IPs
                alert = {
                    'level': 'MEDIUM',
                    'type': 'SUSPICIOUS_ACTIVITY',
                    'user': row[0],
                    'action': row[1],
                    'count': row[2],
                    'ips': row[3]
                }
                alerts.append(alert)
                print(f"⚠️ Suspicious activity: {row[0]} - {row[1]} from {len(row[3])} IPs")
        
        return alerts
    
    def check_unauthorized_access(self) -> List[Dict]:
        """Check for unauthorized access attempts"""
        
        sql = """
            SELECT username, action, resource, status, ip_address, timestamp
            FROM audit_logs
            WHERE status = 'failure'
              AND timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY timestamp DESC
            LIMIT 100
        """
        
        with self.engine.connect() as conn:
            results = conn.execute(text(sql)).fetchall()
        
        alerts = []
        ip_failures = defaultdict(int)
        
        for row in results:
            ip_failures[row[4]] += 1
            
        for ip, count in ip_failures.items():
            if count > 10:
                alert = {
                    'level': 'HIGH',
                    'type': 'UNAUTHORIZED_ACCESS',
                    'ip': ip,
                    'attempts': count
                }
                alerts.append(alert)
                print(f"⚠️ Unauthorized access from IP {ip}: {count} attempts")
        
        return alerts
    
    def check_api_health(self) -> Dict:
        """Check API health and security status"""
        
        try:
            response = requests.get(f"{API_URL}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Status: {data.get('status', 'unknown')}")
                print(f"   Security: {data.get('security', 'unknown')}")
                return {'status': 'healthy', 'data': data}
            else:
                print(f"❌ API unhealthy: {response.status_code}")
                return {'status': 'unhealthy', 'code': response.status_code}
        except Exception as e:
            print(f"❌ API unreachable: {e}")
            return {'status': 'unreachable', 'error': str(e)}
    
    def check_audit_log_growth(self) -> Dict:
        """Monitor audit log growth rate"""
        
        sql = """
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as count
            FROM audit_logs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour DESC
        """
        
        with self.engine.connect() as conn:
            results = conn.execute(text(sql)).fetchall()
        
        if results:
            recent_rate = results[0][1] if results else 0
            avg_rate = sum(r[1] for r in results) / len(results) if results else 0
            
            if recent_rate > avg_rate * 3:
                print(f"⚠️ Unusual audit log growth: {recent_rate} logs/hour (avg: {avg_rate:.1f})")
                return {
                    'alert': True,
                    'recent': recent_rate,
                    'average': avg_rate
                }
            else:
                print(f"✅ Normal audit log rate: {recent_rate} logs/hour")
                return {
                    'alert': False,
                    'recent': recent_rate,
                    'average': avg_rate
                }
        return {'alert': False, 'recent': 0, 'average': 0}
    
    def check_session_anomalies(self) -> List[Dict]:
        """Check for session anomalies"""
        
        sql = """
            SELECT u.username, COUNT(s.id) as active_sessions,
                   array_agg(DISTINCT s.ip_address) as ips
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.expires_at > NOW()
              AND s.revoked = FALSE
            GROUP BY u.username
            HAVING COUNT(s.id) > 3
        """
        
        with self.engine.connect() as conn:
            results = conn.execute(text(sql)).fetchall()
        
        alerts = []
        for row in results:
            alert = {
                'level': 'MEDIUM',
                'type': 'SESSION_ANOMALY',
                'user': row[0],
                'sessions': row[1],
                'ips': row[2]
            }
            alerts.append(alert)
            print(f"⚠️ Multiple sessions: {row[0]} has {row[1]} active sessions")
        
        return alerts
    
    def generate_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'api_health': self.check_api_health(),
            'failed_logins': self.check_failed_logins(),
            'suspicious_activity': self.check_suspicious_activity(),
            'unauthorized_access': self.check_unauthorized_access(),
            'audit_log_growth': self.check_audit_log_growth(),
            'session_anomalies': self.check_session_anomalies()
        }
        
        # Count alerts by severity
        all_alerts = []
        all_alerts.extend(report['failed_logins'])
        all_alerts.extend(report['suspicious_activity'])
        all_alerts.extend(report['unauthorized_access'])
        all_alerts.extend(report['session_anomalies'])
        
        report['summary'] = {
            'total_alerts': len(all_alerts),
            'high': len([a for a in all_alerts if a.get('level') == 'HIGH']),
            'medium': len([a for a in all_alerts if a.get('level') == 'MEDIUM']),
            'low': len([a for a in all_alerts if a.get('level') == 'LOW'])
        }
        
        return report
    
    def send_alert(self, alert: Dict):
        """Send alert to webhook"""
        
        if not ALERT_WEBHOOK:
            return
        
        message = {
            'text': f"🚨 NEXA Security Alert",
            'attachments': [{
                'color': 'danger' if alert['level'] == 'HIGH' else 'warning',
                'title': alert['type'],
                'fields': [
                    {'title': k, 'value': str(v), 'short': True}
                    for k, v in alert.items()
                ],
                'timestamp': datetime.now().isoformat()
            }]
        }
        
        try:
            requests.post(ALERT_WEBHOOK, json=message)
        except:
            pass  # Silent fail for webhook

def main():
    """Main monitoring loop"""
    
    print("="*70)
    print("NEXA SECURITY MONITORING DASHBOARD")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print(f"API: {API_URL}")
    print("-"*70)
    
    monitor = SecurityMonitor()
    
    # Continuous monitoring mode
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        print("\n📊 Continuous monitoring mode (Ctrl+C to stop)")
        
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running security checks...")
                report = monitor.generate_security_report()
                
                # Send alerts for high severity issues
                if report['summary']['high'] > 0:
                    print(f"\n🚨 {report['summary']['high']} HIGH severity alerts!")
                    for category in ['failed_logins', 'unauthorized_access']:
                        for alert in report.get(category, []):
                            if alert.get('level') == 'HIGH':
                                monitor.send_alert(alert)
                
                # Sleep for 5 minutes
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
    
    else:
        # Single run mode
        report = monitor.generate_security_report()
        
        # Display summary
        print("\n" + "="*70)
        print("SECURITY REPORT SUMMARY")
        print("="*70)
        print(f"Total Alerts: {report['summary']['total_alerts']}")
        print(f"  High:   {report['summary']['high']}")
        print(f"  Medium: {report['summary']['medium']}")
        print(f"  Low:    {report['summary']['low']}")
        
        # Save report
        report_file = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Recommendations
        if report['summary']['total_alerts'] > 0:
            print("\n" + "="*70)
            print("RECOMMENDED ACTIONS")
            print("="*70)
            
            if report['summary']['high'] > 0:
                print("\n🚨 HIGH PRIORITY:")
                print("1. Review and lock compromised accounts")
                print("2. Check firewall rules for suspicious IPs")
                print("3. Rotate admin credentials")
                print("4. Enable 2FA for all admin accounts")
            
            if report['failed_logins']:
                print("\n⚠️ Failed Logins:")
                print("1. Reset passwords for affected accounts")
                print("2. Implement account lockout policy")
                print("3. Consider IP-based rate limiting")
            
            if report['unauthorized_access']:
                print("\n⚠️ Unauthorized Access:")
                print("1. Block suspicious IP addresses")
                print("2. Review API permissions")
                print("3. Implement geo-blocking if needed")

if __name__ == "__main__":
    main()
