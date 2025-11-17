"""
Vercel Serverless Function Entry Point
This file is required for Vercel to run Flask as a serverless function
"""
from app import create_app

# Create Flask app instance
app = create_app()

# Vercel expects the app to be exported directly
# The @vercel/python builder will automatically wrap it
__all__ = ['app']
