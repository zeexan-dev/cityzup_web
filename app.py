from project import db, create_app, models
from project.models import insert_default_user, insert_default_campaigns

# Create the Flask app
app = create_app()
# Create the database tables
with app.app_context():
    db.create_all()
    # insert_default_user()
    insert_default_campaigns()  # Insert default campaigns

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)