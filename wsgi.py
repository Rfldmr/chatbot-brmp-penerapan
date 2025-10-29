"""
WSGI Entry Point for Production Deployment
Gunakan file ini untuk menjalankan aplikasi di production dengan Waitress/Gunicorn
"""

from app import app

if __name__ == "__main__":
    # Production server menggunakan Waitress (Windows-friendly)
    try:
        from waitress import serve
        print("\n" + "="*60)
        print("🚀 Chatbot BRMP Production Server (Waitress)")
        print("="*60)
        print("📍 URL: http://localhost:5000")
        print("📍 Admin: http://localhost:5000/admin/login")
        print("✅ Production-ready WSGI server")
        print("="*60 + "\n")
        
        # Serve aplikasi dengan Waitress
        serve(app, host='0.0.0.0', port=5000, threads=4)
    except ImportError:
        print("\n⚠️  Waitress belum terinstall!")
        print("Install dengan: pip install waitress")
        print("Atau jalankan: python app.py (development mode)\n")
