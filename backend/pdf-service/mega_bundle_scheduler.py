#!/usr/bin/env python3
"""
Mega Bundle Scheduler - Optimizes job scheduling for maximum profitability
Handles dependencies, geographic clustering, and resource allocation
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
from datetime import datetime, timedelta
from sklearn.cluster import DBSCAN
from scipy.spatial import distance_matrix
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScheduledJob:
    """Represents a scheduled job with timing"""
    job_id: str
    tag: str
    day: int
    start_hour: float
    duration: float
    crew_id: str
    zone: str
    coordinates: Tuple[float, float]
    profit: float
    dependencies_met: bool

class MegaBundleScheduler:
    """
    Advanced scheduling optimizer for mega bundles
    """
    
    def __init__(self):
        """Initialize scheduler with default parameters"""
        
        self.crew_types = {
            "pole_crew": {
                "capacity": 12,  # hours per day
                "skills": ["07D", "KAA", "2AA"],
                "cost_per_hour": 500  # crew cost
            },
            "underground_crew": {
                "capacity": 12,
                "skills": ["UG1"],
                "cost_per_hour": 600
            },
            "transformer_crew": {
                "capacity": 12,
                "skills": ["TRX", "KAA"],
                "cost_per_hour": 550
            }
        }
        
        self.travel_speed_mph = 30  # Average travel speed
        self.setup_time_hours = 0.5  # Setup time per job
        self.min_cluster_size = 5  # Minimum jobs per geographic cluster
        
    def optimize_schedule(self,
                         jobs: List[Dict],
                         estimates: Dict[str, Any],
                         max_daily_hours: int = 12,
                         prioritize: str = "profit",
                         num_crews: int = 3) -> Dict:
        """
        Optimize job scheduling with multiple constraints
        
        Args:
            jobs: List of job dictionaries
            estimates: Cost estimates by job ID
            max_daily_hours: Maximum working hours per day
            prioritize: Optimization priority (profit/schedule/compliance)
            num_crews: Number of available crews
            
        Returns:
            Optimized schedule with crew assignments
        """
        
        if not jobs:
            return {"error": "No jobs to schedule"}
        
        # Convert jobs to internal format
        job_list = self._prepare_jobs(jobs, estimates)
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(job_list)
        
        # Cluster jobs geographically
        clusters = self._cluster_by_geography(job_list)
        
        # Apply prioritization strategy
        if prioritize == "profit":
            job_list = self._prioritize_by_profit(job_list, estimates)
        elif prioritize == "compliance":
            job_list = self._prioritize_by_compliance(job_list)
        else:  # schedule
            job_list = self._prioritize_by_efficiency(job_list, clusters)
        
        # Run scheduling algorithm
        schedule = self._create_schedule(
            job_list,
            dependency_graph,
            clusters,
            max_daily_hours,
            num_crews
        )
        
        # Calculate metrics
        metrics = self._calculate_schedule_metrics(schedule, estimates)
        
        return {
            "schedule": schedule,
            "metrics": metrics,
            "clusters": len(clusters),
            "optimization_method": prioritize,
            "constraints_applied": [
                "Dependencies respected",
                "Geographic clustering",
                f"Max {max_daily_hours} hours/day",
                f"{num_crews} crews available"
            ]
        }
    
    def _prepare_jobs(self, jobs: List[Dict], estimates: Dict) -> List[Dict]:
        """Prepare and validate job data"""
        
        prepared = []
        for job in jobs:
            # Extract coordinates
            coords = job.get("coordinates", (0, 0))
            if isinstance(coords, str):
                # Parse string coordinates
                try:
                    parts = coords.strip("()").split(",")
                    coords = (float(parts[0]), float(parts[1]))
                except:
                    coords = (0, 0)
            
            # Get profit from estimates
            job_id = job.get("id") or job.get("job_id")
            profit = 0
            if job_id in estimates:
                profit = estimates[job_id].get("profit", 0)
            
            prepared.append({
                "id": job_id,
                "tag": job.get("tag", "UNK"),
                "coordinates": coords,
                "duration": job.get("estimated_hours", {}).get("labor", 8),
                "dependencies": job.get("dependencies", []),
                "compliance_score": job.get("compliance_score", 0.8),
                "profit": profit,
                "priority": job.get("priority", 3)
            })
        
        return prepared
    
    def _build_dependency_graph(self, jobs: List[Dict]) -> Dict[str, List[str]]:
        """Build job dependency graph"""
        
        graph = defaultdict(list)
        jobs_by_location = defaultdict(lambda: defaultdict(list))
        
        # Group jobs by location and tag
        for job in jobs:
            loc_key = f"{job['coordinates'][0]:.2f},{job['coordinates'][1]:.2f}"
            jobs_by_location[loc_key][job['tag']].append(job['id'])
        
        # Apply dependencies within same location
        for loc_key, tags in jobs_by_location.items():
            for job in jobs:
                if f"{job['coordinates'][0]:.2f},{job['coordinates'][1]:.2f}" == loc_key:
                    for dep_tag in job['dependencies']:
                        if dep_tag in tags:
                            # This job depends on all jobs of dep_tag at this location
                            for dep_job_id in tags[dep_tag]:
                                if dep_job_id != job['id']:
                                    graph[job['id']].append(dep_job_id)
        
        return dict(graph)
    
    def _cluster_by_geography(self, jobs: List[Dict], eps_miles: float = 2.0) -> List[List[str]]:
        """
        Cluster jobs by geographic proximity using DBSCAN
        
        Args:
            jobs: List of jobs with coordinates
            eps_miles: Maximum distance between jobs in same cluster (miles)
            
        Returns:
            List of clusters (each cluster is list of job IDs)
        """
        
        if not jobs:
            return []
        
        # Extract coordinates
        coords = np.array([job['coordinates'] for job in jobs])
        
        # Convert lat/lon to approximate miles
        # 1 degree latitude ≈ 69 miles, 1 degree longitude ≈ 55 miles (at 40° latitude)
        coords_miles = coords * np.array([69, 55])
        
        # Use DBSCAN for clustering
        clustering = DBSCAN(eps=eps_miles, min_samples=3).fit(coords_miles)
        
        # Group jobs by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(clustering.labels_):
            if label >= 0:  # -1 means noise/outlier
                clusters[label].append(jobs[idx]['id'])
            else:
                # Create single-job cluster for outliers
                clusters[f"outlier_{idx}"] = [jobs[idx]['id']]
        
        return list(clusters.values())
    
    def _prioritize_by_profit(self, jobs: List[Dict], estimates: Dict) -> List[Dict]:
        """Sort jobs by profitability"""
        return sorted(jobs, key=lambda j: j.get('profit', 0), reverse=True)
    
    def _prioritize_by_compliance(self, jobs: List[Dict]) -> List[Dict]:
        """Sort jobs by compliance score and priority"""
        return sorted(jobs, key=lambda j: (
            -j.get('compliance_score', 0),
            j.get('priority', 999)
        ))
    
    def _prioritize_by_efficiency(self, jobs: List[Dict], clusters: List[List[str]]) -> List[Dict]:
        """Sort jobs to minimize travel time"""
        
        # Create job lookup
        job_lookup = {job['id']: job for job in jobs}
        
        # Process clusters in order of size (largest first)
        sorted_clusters = sorted(clusters, key=len, reverse=True)
        
        ordered_jobs = []
        for cluster in sorted_clusters:
            # Within cluster, sort by tag priority to respect dependencies
            cluster_jobs = [job_lookup[job_id] for job_id in cluster if job_id in job_lookup]
            cluster_jobs.sort(key=lambda j: j.get('priority', 999))
            ordered_jobs.extend(cluster_jobs)
        
        # Add any jobs not in clusters
        clustered_ids = set(job_id for cluster in clusters for job_id in cluster)
        remaining = [job for job in jobs if job['id'] not in clustered_ids]
        ordered_jobs.extend(remaining)
        
        return ordered_jobs
    
    def _create_schedule(self,
                        jobs: List[Dict],
                        dependencies: Dict[str, List[str]],
                        clusters: List[List[str]],
                        max_daily_hours: int,
                        num_crews: int) -> Dict:
        """
        Create detailed schedule with crew assignments
        
        Returns:
            Schedule with days, crews, and job assignments
        """
        
        schedule = {
            "days": [],
            "crews": [],
            "total_days": 0,
            "total_travel_hours": 0
        }
        
        # Initialize crews
        for i in range(num_crews):
            crew_type = list(self.crew_types.keys())[i % len(self.crew_types)]
            schedule["crews"].append({
                "id": f"crew_{i+1}",
                "type": crew_type,
                "capacity": self.crew_types[crew_type]["capacity"],
                "skills": self.crew_types[crew_type]["skills"]
            })
        
        # Track completed jobs for dependencies
        completed = set()
        scheduled = []
        
        # Create day-by-day schedule
        current_day = 1
        max_days = 365  # Safety limit
        
        while len(scheduled) < len(jobs) and current_day <= max_days:
            day_schedule = {
                "day": current_day,
                "date": (datetime.now() + timedelta(days=current_day-1)).strftime("%Y-%m-%d"),
                "crews": []
            }
            
            # Schedule jobs for each crew
            for crew in schedule["crews"]:
                crew_day = {
                    "crew_id": crew["id"],
                    "jobs": [],
                    "total_hours": 0,
                    "travel_hours": 0,
                    "zones": []
                }
                
                # Find available jobs for this crew
                available_jobs = []
                for job in jobs:
                    if job['id'] in [s['id'] for s in scheduled]:
                        continue  # Already scheduled
                    
                    # Check dependencies
                    job_deps = dependencies.get(job['id'], [])
                    if all(dep in completed for dep in job_deps):
                        # Check crew skills
                        if job['tag'] in crew['skills']:
                            available_jobs.append(job)
                
                # Schedule jobs for this crew today
                for job in available_jobs:
                    if crew_day['total_hours'] + job['duration'] <= max_daily_hours:
                        crew_day['jobs'].append({
                            "id": job['id'],
                            "tag": job['tag'],
                            "duration": job['duration'],
                            "start_hour": crew_day['total_hours'],
                            "coordinates": job['coordinates']
                        })
                        crew_day['total_hours'] += job['duration']
                        
                        # Track zone
                        zone = self._get_zone_for_coordinates(job['coordinates'], clusters)
                        if zone not in crew_day['zones']:
                            crew_day['zones'].append(zone)
                        
                        scheduled.append({"id": job['id'], "day": current_day, "crew": crew["id"]})
                        
                        # Stop if day is full
                        if crew_day['total_hours'] >= max_daily_hours - 2:
                            break
                
                # Calculate travel time for this crew
                if len(crew_day['jobs']) > 1:
                    crew_day['travel_hours'] = self._calculate_travel_time(crew_day['jobs'])
                    schedule['total_travel_hours'] += crew_day['travel_hours']
                
                if crew_day['jobs']:
                    day_schedule['crews'].append(crew_day)
                
                # Mark jobs as completed at end of day
                for job in crew_day['jobs']:
                    completed.add(job['id'])
            
            if day_schedule['crews']:
                schedule['days'].append(day_schedule)
            
            current_day += 1
            
            # Break if no progress (circular dependencies or no available jobs)
            if not any(crew['jobs'] for crew in day_schedule.get('crews', [])):
                logger.warning(f"No progress on day {current_day}, stopping schedule")
                break
        
        schedule['total_days'] = len(schedule['days'])
        
        # Add summary
        schedule['summary'] = {
            "jobs_scheduled": len(scheduled),
            "jobs_unscheduled": len(jobs) - len(scheduled),
            "average_utilization": self._calculate_utilization(schedule),
            "travel_efficiency": f"{100 - (schedule['total_travel_hours'] / max(1, sum(j['duration'] for j in jobs)) * 100):.1f}%"
        }
        
        return schedule
    
    def _get_zone_for_coordinates(self, coords: Tuple[float, float], clusters: List[List[str]]) -> str:
        """Determine zone label for coordinates"""
        
        # Simple zone naming based on quadrant
        lat, lon = coords
        if lat >= 0 and lon >= 0:
            return "Zone_NE"
        elif lat >= 0 and lon < 0:
            return "Zone_NW"
        elif lat < 0 and lon >= 0:
            return "Zone_SE"
        else:
            return "Zone_SW"
    
    def _calculate_travel_time(self, jobs: List[Dict]) -> float:
        """Calculate travel time between jobs"""
        
        if len(jobs) <= 1:
            return 0
        
        total_hours = 0
        for i in range(1, len(jobs)):
            # Calculate distance between consecutive jobs
            coords1 = jobs[i-1]['coordinates']
            coords2 = jobs[i]['coordinates']
            
            # Approximate distance in miles
            lat_diff = abs(coords1[0] - coords2[0]) * 69
            lon_diff = abs(coords1[1] - coords2[1]) * 55
            distance = np.sqrt(lat_diff**2 + lon_diff**2)
            
            # Calculate travel time
            travel_hours = distance / self.travel_speed_mph
            total_hours += travel_hours
        
        return round(total_hours, 2)
    
    def _calculate_utilization(self, schedule: Dict) -> float:
        """Calculate average crew utilization"""
        
        if not schedule['days']:
            return 0
        
        total_capacity = 0
        total_used = 0
        
        for day in schedule['days']:
            for crew_day in day['crews']:
                total_capacity += 12  # Max hours per day
                total_used += crew_day['total_hours']
        
        if total_capacity == 0:
            return 0
        
        return round((total_used / total_capacity) * 100, 1)
    
    def _calculate_schedule_metrics(self, schedule: Dict, estimates: Dict) -> Dict:
        """Calculate comprehensive schedule metrics"""
        
        metrics = {
            "total_days": schedule['total_days'],
            "total_crews": len(schedule['crews']),
            "average_daily_profit": 0,
            "peak_day_jobs": 0,
            "efficiency_score": 0,
            "cost_breakdown": {
                "labor": 0,
                "travel": 0,
                "overhead": 0
            }
        }
        
        if not schedule['days']:
            return metrics
        
        daily_profits = []
        daily_job_counts = []
        
        for day in schedule['days']:
            day_profit = 0
            day_jobs = 0
            
            for crew_day in day['crews']:
                for job in crew_day['jobs']:
                    day_jobs += 1
                    if job['id'] in estimates:
                        day_profit += estimates[job['id']].get('profit', 0)
                
                # Add crew costs
                crew_type = next((c['type'] for c in schedule['crews'] if c['id'] == crew_day['crew_id']), None)
                if crew_type and crew_type in self.crew_types:
                    crew_cost = self.crew_types[crew_type]['cost_per_hour'] * crew_day['total_hours']
                    metrics['cost_breakdown']['labor'] += crew_cost
                
                # Add travel costs
                travel_cost = crew_day['travel_hours'] * 50  # $50/hour travel cost
                metrics['cost_breakdown']['travel'] += travel_cost
            
            daily_profits.append(day_profit)
            daily_job_counts.append(day_jobs)
        
        metrics['average_daily_profit'] = round(np.mean(daily_profits) if daily_profits else 0, 2)
        metrics['peak_day_jobs'] = max(daily_job_counts) if daily_job_counts else 0
        
        # Calculate efficiency score (0-100)
        utilization = schedule['summary']['average_utilization']
        travel_efficiency = float(schedule['summary']['travel_efficiency'].rstrip('%'))
        metrics['efficiency_score'] = round((utilization + travel_efficiency) / 2, 1)
        
        # Add overhead (15% of labor + travel)
        metrics['cost_breakdown']['overhead'] = (
            metrics['cost_breakdown']['labor'] + 
            metrics['cost_breakdown']['travel']
        ) * 0.15
        
        return metrics
