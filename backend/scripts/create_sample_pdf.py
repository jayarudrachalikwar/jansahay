"""Create the development sample PDF used for Phase 6 RAG testing."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "50 780 Td"]
    for line in lines:
        escaped = _escape_pdf_text(line)
        commands.append(f"({escaped}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("utf-8")


def build_sample_pdf_bytes() -> bytes:
    page_texts = [
        [
            "DEVELOPMENT SAMPLE - NOT OFFICIAL GOVERNMENT DATA",
            "Sample Crop Insurance Support Scheme",
            "",
            "Purpose:",
            "This fictional development document explains a sample crop insurance support",
            "program for testing JanSahay AI document retrieval.",
            "",
            "Benefits:",
            "- Subsidized crop insurance premium for eligible farmers",
            "- Compensation support for notified crop losses",
            "- Guidance for filing insurance claims after crop damage",
        ],
        [
            "DEVELOPMENT SAMPLE - NOT OFFICIAL GOVERNMENT DATA",
            "Eligibility (Sample Document Content):",
            "- Farmer must cultivate notified crops such as cotton, paddy, or maize",
            "- Farmer must reside in the covered state mentioned in the application",
            "- Land records and crop sowing details may be required for verification",
            "",
            "Application Documents Required:",
            "- Aadhaar-linked identity proof (sample requirement)",
            "- Land ownership or cultivation proof",
            "- Bank account details for claim settlement",
            "- Crop sowing certificate or field inspection report where applicable",
        ],
        [
            "DEVELOPMENT SAMPLE - NOT OFFICIAL GOVERNMENT DATA",
            "Application Process:",
            "1. Visit the local agriculture office or authorized enrollment center.",
            "2. Submit the required documents listed in this sample document.",
            "3. Pay the farmer share of the insurance premium if applicable.",
            "4. Keep the enrollment receipt for future claim reference.",
            "",
            "Important Note:",
            "This PDF is development sample data for JanSahay Phase 6 RAG testing only.",
            "It is not an official government document.",
        ],
    ]

    writer = PdfWriter()
    font_ref = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )

    for page_lines in page_texts:
        page = PageObject.create_blank_page(width=612, height=792)
        content_stream = DecodedStreamObject()
        content_stream.set_data(_page_stream(page_lines))
        content_ref = writer._add_object(content_stream)

        resources = DictionaryObject()
        font_dict = DictionaryObject({NameObject("/F1"): font_ref})
        resources[NameObject("/Font")] = font_dict
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = content_ref

        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def main() -> int:
    output = Path(__file__).resolve().parents[1] / "data" / "documents" / "sample_crop_insurance.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_sample_pdf_bytes())
    print(f"Created sample PDF: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
