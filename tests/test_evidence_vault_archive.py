import os
import zipfile
from pathlib import Path
from pypdf import PdfReader
from app.models.auth import User, Role
from app.models.organization import Organization, OrganizationUser
from app.models.base import db


def test_statutory_evidence_vault_files_and_watermarks():
    """Verifies that all evidence files in the categorized vault exist,

    are non-blank (>4KB), and contain the embedded security watermark.
    """
    vault_dir = Path("downloads/CRAS_Statutory_Evidence_Vault")
    assert vault_dir.exists(), "Vault directory must exist"

    expected_folders = [
        "01_Data_Protection_Compliance_ODPC",
        "02_Tax_Compliance_KRA",
        "03_Employment_and_Labour_Compliance",
        "04_Evidence_By_Company/Apex_Logistics_Solutions_Ltd",
        "04_Evidence_By_Company/Kilimani_Healthcare_Centre_Ltd",
        "04_Evidence_By_Company/Rift_Valley_Fresh_Produce_Ltd",
        "04_Evidence_By_Company/Savanna_Retail_Enterprises_Ltd",
    ]

    total_pdf_count = 0
    for sub in expected_folders:
        folder_path = vault_dir / sub
        assert folder_path.exists(), f"Subfolder {sub} must exist"
        pdf_files = list(folder_path.glob("*.pdf"))
        assert len(pdf_files) > 0, f"Subfolder {sub} must contain PDFs"

        for pdf in pdf_files:
            total_pdf_count += 1
            size = pdf.stat().st_size
            assert size >= 4000, f"PDF {pdf.name} is undersized ({size} bytes)"

            # Verify text and watermark extraction
            reader = PdfReader(str(pdf))
            assert len(reader.pages) >= 1
            extracted = reader.pages[0].extract_text()
            assert len(extracted) > 200, f"PDF {pdf.name} has insufficient text ({len(extracted)} chars)"
            assert "STATUTORY" in extracted or "EVIDENCE" in extracted, f"Watermark missing in {pdf.name}"

    assert total_pdf_count == 40, f"Expected 40 PDFs in vault, found {total_pdf_count}"


def test_statutory_evidence_zip_archive():
    """Verifies that the ZIP archive is valid, non-corrupted, and contains all 40 files."""
    zip_path = Path("downloads/CRAS_Statutory_Evidence_Vault.zip")
    assert zip_path.exists(), "ZIP archive must exist"
    assert zip_path.stat().st_size > 50000, "ZIP archive should be > 50KB"

    with zipfile.ZipFile(str(zip_path), "r") as zf:
        namelist = zf.namelist()
        pdf_names = [n for n in namelist if n.endswith(".pdf")]
        assert len(pdf_names) == 40, f"Expected 40 PDFs in ZIP, found {len(pdf_names)}"
        # Verify first file extractable
        data = zf.read(pdf_names[0])
        assert len(data) > 4000


def test_download_evidence_archive_route(client, app):
    """Verifies that the /evidence/download-archive endpoint returns the ZIP archive."""
    with app.app_context():
        user = User.query.first()
        if not user:
            user = User(email="archive_tester@cras.ke", full_name="Archive Tester")
            user.set_password("Admin@CRAS2026!")
            db.session.add(user)
            db.session.commit()

        org = Organization.query.first()
        if not org:
            org = Organization(
                name="Test Org Archive",
                business_registration_number="CPR/2026/99",
                kra_pin="P059999999Z",
                contact_email="archive@testorg.co.ke"
            )
            db.session.add(org)
            db.session.commit()

        # Link user to org
        role = Role.query.filter_by(name=Role.ORG_ADMIN).first()
        membership = OrganizationUser.query.filter_by(user_id=user.id, organization_id=org.id).first()
        if not membership:
            db.session.add(OrganizationUser(user_id=user.id, organization_id=org.id, role_id=role.id if role else 1, is_primary=True))
            db.session.commit()

        user_id = user.id
        org_id = org.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["active_org_id"] = org_id
        sess["_fresh"] = True

    resp = client.get("/evidence/download-archive")
    assert resp.status_code == 200
    assert resp.mimetype == "application/zip"
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    assert "CRAS_Statutory_Evidence_Vault.zip" in resp.headers.get("Content-Disposition", "")
    assert len(resp.data) > 50000
