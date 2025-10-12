#!/usr/bin/env python3
"""
FastAPI Endpoints for Mega Bundle Processing
Integrates with existing NEXA system
"""

from fastapi import APIRouter, UploadFile, File, Query, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import shutil
import logging
from pathlib import Path
from datetime import datetime
import json

from mega_bundle_analyzer import MegaBundleAnalyzer
from mega_bundle_scheduler import MegaBundleScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mega-bundle", tags=["Mega Bundle Analysis"])

# Initialize analyzer and scheduler
analyzer = MegaBundleAnalyzer()
scheduler = MegaBundleScheduler()

# Store processing status (in production, use Redis)
processing_status = {}

@router.post("/upload")
async def upload_mega_bundle(
    background_tasks: BackgroundTasks,
    job_zip: UploadFile = File(..., description="ZIP file containing job PDFs (3500+)"),
    bid_sheet: UploadFile = File(None, description="Bid sheet PDF/CSV with unit prices"),
    contract: UploadFile = File(None, description="Contract PDF with rates"),
    mode: str = Query("post-win", regex="^(post-win|pre-bid)$", description="Analysis mode"),
    profit_margin: float = Query(0.20, ge=0, le=1, description="Target profit margin (0-1)"),
    max_daily_hours: int = Query(12, ge=8, le=16, description="Max working hours per day"),
    prioritize: str = Query("profit", regex="^(profit|schedule|compliance)$", description="Optimization priority")
):
    """
    Upload and process a mega bundle of job packages
    
    Modes:
    - **post-win**: Analyze profitability with known contract rates
    - **pre-bid**: Estimate costs and recommend minimum bid
    
    Returns bundle ID for status tracking
    """
    
    # Validate file sizes
    if job_zip.size > 1024 * 1024 * 500:  # 500MB limit
        raise HTTPException(status_code=413, detail="ZIP file too large (max 500MB)")
    
    # Create bundle ID
    bundle_id = datetime.now().strftime("MB_%Y%m%d_%H%M%S")
    
    # Save uploaded files
    temp_dir = Path("/tmp") / "mega_bundle_upload" / bundle_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save ZIP
        zip_path = temp_dir / "jobs.zip"
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(job_zip.file, f)
        logger.info(f"Saved ZIP file: {zip_path} ({job_zip.size / 1024 / 1024:.1f} MB)")
        
        # Save optional files
        bid_path = None
        if bid_sheet:
            bid_path = temp_dir / f"bid.{bid_sheet.filename.split('.')[-1]}"
            with open(bid_path, 'wb') as f:
                shutil.copyfileobj(bid_sheet.file, f)
        
        contract_path = None
        if contract:
            contract_path = temp_dir / "contract.pdf"
            with open(contract_path, 'wb') as f:
                shutil.copyfileobj(contract.file, f)
        
        # Initialize status
        processing_status[bundle_id] = {
            "status": "processing",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "mode": mode,
            "files": {
                "job_count": "counting...",
                "has_bid": bid_sheet is not None,
                "has_contract": contract is not None
            }
        }
        
        # Process in background
        background_tasks.add_task(
            process_bundle_async,
            bundle_id,
            str(zip_path),
            str(bid_path) if bid_path else None,
            str(contract_path) if contract_path else None,
            mode,
            profit_margin,
            max_daily_hours,
            prioritize
        )
        
        return {
            "bundle_id": bundle_id,
            "status": "processing",
            "message": f"Bundle uploaded successfully. Processing in {'pre-bid' if mode == 'pre-bid' else 'post-win'} mode",
            "poll_url": f"/mega-bundle/status/{bundle_id}",
            "estimated_time": "5-10 minutes for 3500 jobs"
        }
        
    except Exception as e:
        logger.error(f"Upload failed for bundle {bundle_id}: {e}")
        processing_status[bundle_id] = {
            "status": "failed",
            "error": str(e)
        }
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {e}")

async def process_bundle_async(
    bundle_id: str,
    zip_path: str,
    bid_path: Optional[str],
    contract_path: Optional[str],
    mode: str,
    profit_margin: float,
    max_daily_hours: int,
    prioritize: str
):
    """Background task to process bundle"""
    
    try:
        logger.info(f"Starting async processing for bundle {bundle_id}")
        
        # Update status
        processing_status[bundle_id]["status"] = "analyzing"
        processing_status[bundle_id]["progress"] = 10
        
        # Run analysis
        result = analyzer.analyze_bundle(
            zip_path,
            bid_path,
            contract_path,
            mode,
            profit_margin
        )
        
        # Update with job count
        processing_status[bundle_id]["files"]["job_count"] = result["summary"]["total_jobs"]
        processing_status[bundle_id]["progress"] = 50
        
        # Run scheduling optimization
        if result["summary"]["total_jobs"] > 0:
            schedule_result = scheduler.optimize_schedule(
                result.get("jobs", []),
                result.get("estimates", {}),
                max_daily_hours=max_daily_hours,
                prioritize=prioritize
            )
            result["optimized_schedule"] = schedule_result
        
        processing_status[bundle_id]["progress"] = 90
        
        # Save results
        results_dir = Path("/data/mega_bundles") / bundle_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        with open(results_dir / "analysis.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Update final status
        processing_status[bundle_id] = {
            "status": "complete",
            "progress": 100,
            "completion_time": datetime.now().isoformat(),
            "summary": result["summary"],
            "bid_recommendation": result.get("bid_recommendation"),
            "download_url": f"/mega-bundle/download/{bundle_id}"
        }
        
        logger.info(f"Bundle {bundle_id} processing complete")
        
    except Exception as e:
        logger.error(f"Bundle {bundle_id} processing failed: {e}")
        processing_status[bundle_id] = {
            "status": "failed",
            "error": str(e),
            "completion_time": datetime.now().isoformat()
        }
    
    finally:
        # Cleanup temp files
        temp_dir = Path("/tmp/mega_bundle_upload") / bundle_id
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/status/{bundle_id}")
async def get_bundle_status(bundle_id: str):
    """
    Get processing status for a bundle
    
    Returns current status, progress, and results if complete
    """
    
    if bundle_id not in processing_status:
        # Check if results exist on disk
        results_path = Path("/data/mega_bundles") / bundle_id / "analysis.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                result = json.load(f)
                return {
                    "status": "complete",
                    "bundle_id": bundle_id,
                    "summary": result.get("summary"),
                    "download_url": f"/mega-bundle/download/{bundle_id}"
                }
        else:
            raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} not found")
    
    return processing_status[bundle_id]

@router.get("/download/{bundle_id}")
async def download_results(
    bundle_id: str,
    format: str = Query("json", regex="^(json|excel|pdf)$", description="Output format")
):
    """
    Download analysis results
    
    Formats:
    - json: Full analysis data
    - excel: Formatted spreadsheet
    - pdf: Executive summary report
    """
    
    results_path = Path("/data/mega_bundles") / bundle_id / "analysis.json"
    
    if not results_path.exists():
        raise HTTPException(status_code=404, detail=f"Results not found for bundle {bundle_id}")
    
    with open(results_path, 'r') as f:
        result = json.load(f)
    
    if format == "json":
        return JSONResponse(content=result)
    
    elif format == "excel":
        # Create Excel file
        excel_path = create_excel_report(bundle_id, result)
        from fastapi.responses import FileResponse
        return FileResponse(
            excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"mega_bundle_{bundle_id}.xlsx"
        )
    
    elif format == "pdf":
        # Create PDF report
        pdf_path = create_pdf_report(bundle_id, result)
        from fastapi.responses import FileResponse
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"mega_bundle_{bundle_id}.pdf"
        )

@router.get("/list")
async def list_bundles(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List processed bundles
    
    Returns list of bundle IDs with summary info
    """
    
    bundles_dir = Path("/data/mega_bundles")
    
    if not bundles_dir.exists():
        return {"bundles": [], "total": 0}
    
    # Get all bundle directories
    bundle_dirs = sorted(
        [d for d in bundles_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    # Paginate
    total = len(bundle_dirs)
    bundle_dirs = bundle_dirs[offset:offset + limit]
    
    bundles = []
    for bundle_dir in bundle_dirs:
        bundle_id = bundle_dir.name
        analysis_path = bundle_dir / "analysis.json"
        
        if analysis_path.exists():
            with open(analysis_path, 'r') as f:
                result = json.load(f)
                bundles.append({
                    "bundle_id": bundle_id,
                    "created": datetime.fromtimestamp(bundle_dir.stat().st_mtime).isoformat(),
                    "mode": result.get("mode", "unknown"),
                    "total_jobs": result.get("summary", {}).get("total_jobs", 0),
                    "total_profit": result.get("summary", {}).get("total_profit", 0),
                    "profit_margin": result.get("summary", {}).get("profit_margin", "0%")
                })
    
    return {
        "bundles": bundles,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.delete("/{bundle_id}")
async def delete_bundle(bundle_id: str):
    """
    Delete a processed bundle and its results
    """
    
    bundle_dir = Path("/data/mega_bundles") / bundle_id
    
    if not bundle_dir.exists():
        raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} not found")
    
    try:
        shutil.rmtree(bundle_dir)
        
        # Remove from status cache if present
        if bundle_id in processing_status:
            del processing_status[bundle_id]
        
        return {"message": f"Bundle {bundle_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bundle: {e}")

def create_excel_report(bundle_id: str, result: Dict) -> Path:
    """Create Excel report from analysis results"""
    
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    
    excel_path = Path("/data/mega_bundles") / bundle_id / f"report_{bundle_id}.xlsx"
    
    # Create workbook with multiple sheets
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Summary sheet
        summary_df = pd.DataFrame([result["summary"]])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Job details sheet
        if "details" in result:
            details_df = pd.DataFrame(result["details"])
            details_df.to_excel(writer, sheet_name='Job Details', index=False)
        
        # Schedule sheet
        if "optimized_schedule" in result:
            schedule_data = []
            for day in result["optimized_schedule"].get("days", []):
                schedule_data.append({
                    "Day": day["day"],
                    "Zone": day["zone"],
                    "Jobs": len(day["jobs"]),
                    "Hours": day["total_hours"],
                    "Profit": day["total_profit"]
                })
            schedule_df = pd.DataFrame(schedule_data)
            schedule_df.to_excel(writer, sheet_name='Schedule', index=False)
        
        # Format sheets
        workbook = writer.book
        for sheet in workbook.worksheets:
            for cell in sheet[1]:  # Header row
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True)
    
    return excel_path

def create_pdf_report(bundle_id: str, result: Dict) -> Path:
    """Create PDF executive summary from analysis results"""
    
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    
    pdf_path = Path("/data/mega_bundles") / bundle_id / f"report_{bundle_id}.pdf"
    
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f"Mega Bundle Analysis Report - {bundle_id}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Summary section
    summary_data = [
        ["Metric", "Value"],
        ["Total Jobs", str(result["summary"]["total_jobs"])],
        ["Total Cost", f"${result['summary']['total_cost']:,.2f}"],
        ["Total Revenue", f"${result['summary']['total_revenue']:,.2f}"],
        ["Total Profit", f"${result['summary']['total_profit']:,.2f}"],
        ["Profit Margin", result["summary"]["profit_margin"]],
        ["Estimated Days", str(result["summary"].get("estimated_days", "N/A"))]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    
    # Build PDF
    doc.build(story)
    
    return pdf_path

def integrate_mega_bundle_endpoints(app):
    """Add mega bundle router to main app"""
    app.include_router(router)
    logger.info("✅ Mega bundle endpoints registered at /mega-bundle/*")
