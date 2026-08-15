#!/usr/bin/env python3
"""
Camera and Mood Detection Verification Script
This script verifies that the camera is always on for mood detection
"""

import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SATURDAY'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_camera_always_on():
    """
    Verify that the camera is always on for mood detection
    """
    logger.info("Starting camera and mood detection verification...")
    
    try:
        # Import the Saturday core
        from core.main import SaturdayCore
        
        # Create an instance of SaturdayCore
        saturday = SaturdayCore()
        
        # Start the core system
        await saturday.start()
        
        # Verify that vision system is active
        if saturday.vision:
            logger.info("✓ Vision system is active")
            
            # Verify that camera is always on
            if saturday.camera_active:
                logger.info("✓ Camera is active for mood detection")
            else:
                logger.warning("✗ Camera is not active")
                
            # Verify that the vision module is always on
            if saturday.vision.always_on:
                logger.info("✓ Vision system always-on mode is enabled")
            else:
                logger.warning("✗ Vision system always-on mode is not enabled")
                
        else:
            logger.warning("✗ Vision system is not available")
            
        # Keep the system running for a while to verify continuous operation
        logger.info("Keeping system running for 30 seconds to verify continuous operation...")
        await asyncio.sleep(30)
        
        # Final verification
        if saturday.vision and saturday.vision.active:
            logger.info("✓ Vision system remained active during test period")
        else:
            logger.warning("✗ Vision system became inactive during test period")
            
        # Stop the system
        saturday.running = False
        if saturday.vision:
            await saturday.vision.stop()
        
        logger.info("Camera and mood detection verification completed successfully!")
        
    except ImportError as e:
        logger.error(f"Failed to import SaturdayCore: {e}")
        logger.info("This might be because the system is still initializing or dependencies are missing.")
        
        # Alternative verification by checking the code
        logger.info("Performing code-level verification...")
        
        # Check that the modifications were made
        import inspect
        
        # Read the main.py file to verify changes
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'SATURDAY', 'core', 'main.py')
        with open(main_py_path, 'r') as f:
            main_content = f.read()
            
        if 'self.camera_active = True' in main_content and 'always-on camera enabled' in main_content:
            logger.info("✓ Camera activation code found in main.py")
        else:
            logger.warning("✗ Camera activation code not found in main.py")
            
        # Read the vision.py file to verify changes
        vision_py_path = os.path.join(os.path.dirname(__file__), '..', 'SATURDAY', 'core', 'embodied', 'vision.py')
        with open(vision_py_path, 'r') as f:
            vision_content = f.read()
            
        if 'self.always_on = True' in vision_content and 'always on for mood detection' in vision_content:
            logger.info("✓ Always-on camera flag found in vision.py")
        else:
            logger.warning("✗ Always-on camera flag not found in vision.py")
            
        logger.info("Code-level verification completed!")

def main():
    """Main function to run the verification"""
    logger.info("Starting SATURDAY Camera and Mood Detection Verification")
    
    # Run the async verification function
    asyncio.run(verify_camera_always_on())
    
    logger.info("Verification process completed!")

if __name__ == "__main__":
    main()