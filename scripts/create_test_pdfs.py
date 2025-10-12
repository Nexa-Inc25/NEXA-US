from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

os.makedirs("test_documents", exist_ok=True)
spec_book_path = "test_documents/sample_spec_book.pdf"
c = canvas.Canvas(spec_book_path, pagesize=letter)
c.setFont("Helvetica", 12)
c.drawString(100, 750, "Specification Book")
c.drawString(100, 730, "Section 4.1.2: Poles must be buried at least 6 feet deep.")
c.drawString(100, 710, "Section 4.2.1: Conductors must be copper, not aluminum.")
c.drawString(100, 690, "Section 4.2.2: Minimum clearance from ground is 12 feet.")
c.drawString(100, 670, "Section 4.3.1: All bolts must be grade 8.8.")
c.drawString(100, 650, "Section 4.3.2: Insulation must be rated for 600V.")
c.drawString(100, 630, "Section 4.4.1: Anchors must be galvanized steel.")
c.drawString(100, 610, "Section 4.4.2: Minimum anchor depth is 5 feet.")
c.drawString(100, 590, "Section 4.5.1: Crossarms must be fiberglass.")
c.drawString(100, 570, "Section 4.5.2: Maximum pole spacing is 150 feet.")
c.drawString(100, 550, "Section 4.6.1: All hardware must be stainless steel.")
c.save()

audit_report_path = "test_documents/sample_audit_report.pdf"
c = canvas.Canvas(audit_report_path, pagesize=letter)
c.setFont("Helvetica", 12)
c.drawString(100, 750, "Quality Assurance Audit Report")
c.drawString(100, 730, "Infraction 1: Pole buried 4 feet deep in Zone A.")
c.drawString(100, 710, "Infraction 2: Clearance of 10 feet detected in Zone B.")
c.drawString(100, 690, "Infraction 3: Aluminum conductors used in Zone C.")
c.drawString(100, 670, "Infraction 4: Grade 5.6 bolts found in Zone D.")
c.drawString(100, 650, "Infraction 5: Insulation rated at 400V in Zone E.")
c.drawString(100, 630, "Infraction 6: Non-galvanized anchors in Zone F.")
c.drawString(100, 610, "Infraction 7: Anchor depth of 3 feet in Zone G.")
c.drawString(100, 590, "Infraction 8: Wooden crossarms in Zone H.")
c.drawString(100, 570, "Infraction 9: Pole spacing of 200 feet in Zone I.")
c.drawString(100, 550, "Infraction 10: Carbon steel hardware in Zone J.")
c.save()
