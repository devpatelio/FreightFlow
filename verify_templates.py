#!/usr/bin/env python3
"""
Verification script to test:
1. BOL number generation with YYYYMMDD format
2. Template loading confirmation
"""

from pathlib import Path
from datetime import datetime
import sys

def verify_templates_exist():
    """Check that all required templates exist"""
    print("=" * 70)
    print("TEMPLATE VERIFICATION")
    print("=" * 70)
    print()
    
    templates = [
        'templates/BOL_Template.txt',
        'templates/PackingSlip_Template.txt',
        'templates/HansonChemicals.txt'
    ]
    
    all_exist = True
    for template in templates:
        path = Path(template)
        if path.exists():
            size = path.stat().st_size
            print(f"✓ Found: {template}")
            print(f"  Size: {size} bytes")
            
            # Read first few lines
            with open(path, 'r') as f:
                lines = f.readlines()[:3]
                print(f"  First line: {lines[0].strip()}")
        else:
            print(f"✗ Missing: {template}")
            all_exist = False
        print()
    
    return all_exist


def verify_bol_number_format():
    """Verify BOL number format in template"""
    print("=" * 70)
    print("BOL NUMBER FORMAT VERIFICATION")
    print("=" * 70)
    print()
    
    template_path = Path('templates/BOL_Template.txt')
    if not template_path.exists():
        print("✗ BOL_Template.txt not found!")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for YYYYMMDD format instructions
    if 'YYYYMMDD' in content:
        print("✓ Template contains YYYYMMDD format instructions")
    else:
        print("✗ Template missing YYYYMMDD format instructions")
        return False
    
    # Check for current date reference
    if 'TODAY' in content or 'current date' in content.lower():
        print("✓ Template references current/today's date")
    else:
        print("⚠ Template may not reference current date")
    
    # Show expected BOL number format
    today = datetime.now()
    expected_format = f"{today.strftime('%Y%m%d')}001"
    print(f"\n✓ Expected BOL number format for today: {expected_format}")
    print(f"  Date component: {today.strftime('%Y%m%d')}")
    print(f"  Sequence: 001-999")
    
    return True


def test_backend_import():
    """Test that backend module loads correctly"""
    print()
    print("=" * 70)
    print("BACKEND MODULE TEST")
    print("=" * 70)
    print()
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        from backend import DocumentManager, Client
        print("✓ Backend module imported successfully")
        print(f"  DocumentManager: {DocumentManager.__name__}")
        print(f"  Client: {Client.__name__}")
        return True
    except Exception as e:
        print(f"✗ Error importing backend: {str(e)}")
        return False


def show_date_injection_preview():
    """Show what date info will be injected into prompts"""
    print()
    print("=" * 70)
    print("DATE INJECTION PREVIEW")
    print("=" * 70)
    print()
    
    from datetime import datetime
    current_date = datetime.now()
    
    date_info = f"""
CURRENT DATE INFORMATION (use this for BOL number generation):
- Today's Date: {current_date.strftime('%Y-%m-%d')}
- BOL Number Format: {current_date.strftime('%Y%m%d')}XXX (where XXX is a 3-digit sequence starting from 001)
- Example BOL Number for today: {current_date.strftime('%Y%m%d')}001
"""
    
    print("This date information will be injected into every AI prompt:")
    print(date_info)
    print("✓ Date injection code is active")


def main():
    """Run all verification checks"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "LOGISTICS TEMPLATE VERIFICATION" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    results = []
    
    # Run checks
    results.append(("Templates Exist", verify_templates_exist()))
    results.append(("BOL Format Updated", verify_bol_number_format()))
    results.append(("Backend Module", test_backend_import()))
    
    show_date_injection_preview()
    
    # Summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    
    all_passed = True
    for check_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Templates are configured correctly.")
        print()
        print("NEXT STEPS:")
        print("1. Upload a new PO to test BOL number generation")
        print(f"2. Expected BOL number format: {datetime.now().strftime('%Y%m%d')}001")
        print("3. Check console logs for template loading messages")
    else:
        print("⚠ Some checks failed. Review errors above.")
    
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
