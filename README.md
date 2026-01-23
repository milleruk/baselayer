# Base Layer - Fitness & Health Tracking Platform

**Base Layer** is a comprehensive Django-based fitness and health tracking application designed to help users commit to their fitness journey. Built for Power Zone training and running, the platform provides personalized workout plans, challenge tracking, exercise libraries, and progress metrics.

## 🎯 Project Overview

Base Layer is a full-stack web application that enables users to:
- Create and manage personalized weekly workout plans
- Participate in fitness challenges (cycling, running, strength, yoga)
- Track exercises including Kegel, Mobility, and Yoga routines
- Monitor progress with detailed metrics and analytics
- Integrate with Peloton workouts
- Maintain workout history and completion tracking

## 🏗️ Architecture

### Tech Stack
- **Backend**: Django 4.2.27
- **Database**: SQLite (development)
- **Frontend**: 
  - Tailwind CSS (via CDN)
  - Alpine.js for interactivity
  - Chart.js for analytics
- **Python**: 3.12+

### Project Structure

```
pelvicplanner/
├── accounts/          # User authentication and profiles
├── plans/             # Workout plan templates and exercise library
├── tracker/           # Challenge tracking and weekly plans
├── workouts/          # Workout history and completion tracking
├── config/            # Django project configuration
├── templates/         # HTML templates
├── static/            # Static files (CSS, JS)
├── media/             # User-uploaded media files
└── manage.py          # Django management script
```

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Virtual environment support

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pelvicplanner
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   > Note: If `requirements.txt` doesn't exist, install Django and other dependencies manually:
   > ```bash
   > pip install django==4.2.27
   > ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Load initial data (optional)**
   ```bash
   python manage.py seed_plans
   python manage.py seed_challenges
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open your browser and navigate to `http://localhost:8000`
   - Admin panel: `http://localhost:8000/admin`

## 📱 Features

### User Features
- **Dashboard**: Overview of current plans, challenges, and progress
- **Exercise Library**: Browse and view exercises with videos and instructions
- **Weekly Plans**: Personalized workout schedules with daily plan items
- **Challenges**: Join and participate in fitness challenges
- **Metrics**: Track progress with detailed analytics and charts
- **Workout History**: View past workouts and completion records
- **Profile Management**: Update user profile and settings
- **Dark Mode**: Toggle between light and dark themes

### Admin Features
- Challenge management and configuration
- Exercise library management
- Plan template creation
- User administration

## 🔧 Configuration

### Environment Variables

For production, set the following environment variables:

```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

### Database

The project uses SQLite by default for development. For production, configure PostgreSQL or MySQL in `config/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📝 Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

### Management Commands

- `seed_plans`: Populate initial plan templates
- `seed_challenges`: Create sample challenges
- `regenerate_challenge_plans`: Regenerate plans for challenges

## 🗂️ Key Models

- **Exercise**: Exercise library with categories (Kegel, Mobility, Yoga)
- **PlanTemplate**: Reusable weekly workout structures
- **Challenge**: Admin-defined fitness challenges
- **ChallengeInstance**: User participation in challenges
- **WeeklyPlan**: User-specific weekly workout plans
- **DailyPlanItem**: Individual workout items within a week
- **Workout**: Completed workout records

## 🌐 Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Configure proper `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` appropriately
- [ ] Use production database (PostgreSQL/MySQL)
- [ ] Configure static file serving
- [ ] Set up media file storage
- [ ] Configure CSRF trusted origins
- [ ] Set up SSL/HTTPS
- [ ] Configure proper logging
- [ ] Set up backup strategy

### CSRF Trusted Origins

Update `CSRF_TRUSTED_ORIGINS` in `config/settings.py` with your production domain:

```python
CSRF_TRUSTED_ORIGINS = [
    "https://your-domain.com",
]
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and ensure code quality
4. Submit a pull request

## 📄 License

[Specify your license here]

## 👥 Authors

[Add author information]

## 🙏 Acknowledgments

- Built with Django
- UI powered by Tailwind CSS and Alpine.js
- Analytics with Chart.js

## 📞 Support

For issues, questions, or contributions, please [open an issue](link-to-issues) or contact the development team.

---

**Base Layer** — Commit To Be Fit

Built for Power Zone + Running
