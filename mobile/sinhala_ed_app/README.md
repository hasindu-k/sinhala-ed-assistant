# sinhala_ed_app

SinhalaLearn Mobile Application

```

lib/
│── main.dart                  # Entry point
│
├── core/                      # Core utilities shared across app
│   ├── constants/             # App-wide constants (strings, colors, spacing)
│   ├── utils/                 # Helper functions, formatters, validators
│   ├── theme/                 # App themes, typography, styles
│   └── error/                 # Custom error handling
│
├── data/                      # Data layer (API, DB, Models, Repositories)
│   ├── models/                # Data models (User, Task, etc.)
│   ├── services/              # Remote/local services (API calls, DB access)
│   ├── repositories/          # Repository classes combining multiple services
│   └── providers/             # API clients (Dio/HTTP/Firebase, etc.)
│
├── domain/                    # Business logic (optional if following Clean Arch)
│   ├── entities/              # Core entities (abstract models)
│   ├── usecases/              # Application-specific logic
│   └── repositories/          # Abstract repo contracts
│
├── presentation/              # UI Layer
│   ├── pages/                 # Screens (HomePage, LoginPage, etc.)
│   │   └── widgets/           # Page-specific widgets
│   ├── widgets/               # Shared/common widgets
│   ├── controllers/           # State management (Bloc, Provider, Riverpod, GetX)
│   └── routes/                # Route definitions, navigation
│
├── config/                    # Environment & app configuration
│   ├── environment.dart       # Env variables
│   └── app_config.dart        # App-specific config
│
└── injections/                # Dependency injection setup (get_it, riverpod, etc.)

assets/
│── images/                    # Image assets
│── icons/                     # Icon assets
│── fonts/                     # Custom fonts
│── animations/                # Lottie or Rive animations
│── translations/              # i18n files

test/                          # Unit and widget tests
integration_test/              # Integration tests

```

### New Structure
```
lib/
├── main.dart
├── sinhala_ed_app.dart              # Root widget
│
├── core/                            # App-wide utilities
│   ├── constants/
│   ├── i18n/
│   ├── providers/
│   ├── theme/
│   ├── utils/
│   └── widgets/                     # Reusable shared widgets
│
├── data/                            # Data layer
│   ├── models/
│   ├── repositories/
│   └── services/
│
├── features/                        # Feature-based structure
│   ├── auth/                        # Login, register, roles
│   │   ├── view/ (login_page.dart, register_page.dart, etc.)
│   │   ├── controller/ (auth_controller.dart)
│   │   └── model/ (user.dart)
│   │
│   ├── documents/                   # Sinhala doc processing
│   ├── answer_evaluation/           # Answer checking
│   ├── voice_qa/                    # Voice Q&A
│   ├── question_generator/          # Question gen
│   └── settings/                    # Model mgmt, downloads
│
├── presentation/                    # Routing + global UI
│   ├── routes/
│   └── pages/ (only general ones: splash, home, profile)
│
```
