from project import db, create_app, models
from project.models import insert_default_user
# Create the Flask app
app = create_app()

# Create the database tables
with app.app_context():
    db.create_all()
    # insert_default_user()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=443)