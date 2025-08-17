import sys
import traceback
from add_intro_image import Test

def main():
    print("[Test] Running Test.test()...")
    try:
        Test.bulk_test()
        print(f"[Test] Success!")
    except Exception as e:
        print("[Test] Failed with exception:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
