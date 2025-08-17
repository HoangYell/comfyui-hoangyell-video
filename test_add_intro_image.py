import sys
import traceback
from add_intro_image import AddIntroImage

def main():
    print("[Test] Running AddIntroImage.test()...")
    try:
        output_path, output_file = AddIntroImage.test()
        print(f"[Test] Success! Output video path: {output_path}")
    except Exception as e:
        print("[Test] Failed with exception:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
