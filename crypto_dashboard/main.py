from dashboard import Dashboard

def main():
    try:
        app = Dashboard()
        app.run()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
