# Link Manager

A clean, extensible link manager application built with Python and Tkinter, following SOLID principles and design patterns.

## Architecture Overview

This application has been refactored to follow clean architecture principles with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐ │
│  │   Controllers   │  │   UI Components │  │  Dialogs │ │
│  └─────────────────┘  └─────────────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────┤
│                     Business Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │     Services    │  │     Models      │               │
│  └─────────────────┘  └─────────────────┘               │
├─────────────────────────────────────────────────────────┤
│                      Data Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  Repositories   │  │     Utils       │               │
│  └─────────────────┘  └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## SOLID Principles Applied

### 1. Single Responsibility Principle (SRP)
- **`Link`**: Represents a single link entity with its properties and validation
- **`LinkRepository`**: Handles data persistence and retrieval
- **`LinkService`**: Manages business logic operations
- **`BrowserService`**: Handles URL opening functionality
- **`LinkController`**: Coordinates between UI and business logic
- **UI Components**: Each component has a specific UI responsibility

### 2. Open/Closed Principle (OCP)
- **Repository Pattern**: Easy to add new storage backends (database, API) without changing existing code
- **Service Interfaces**: New browser implementations can be added without modifying existing code
- **UI Components**: New UI elements can be added without changing existing components

### 3. Liskov Substitution Principle (LSP)
- **Repository Interface**: Any implementation of `LinkRepository` can be substituted
- **Browser Service Interface**: Any implementation of `BrowserService` can be substituted

### 4. Interface Segregation Principle (ISP)
- **Focused Interfaces**: Each interface has a specific purpose (repository operations, browser operations)
- **Component Callbacks**: UI components have specific callback interfaces

### 5. Dependency Inversion Principle (DIP)
- **Dependency Injection**: High-level modules depend on abstractions, not concretions
- **Service Layer**: Business logic doesn't depend on specific data storage or UI implementations

## Design Patterns Used

### 1. Repository Pattern
- **Purpose**: Abstracts data access logic
- **Implementation**: `LinkRepository` interface with `JsonLinkRepository` implementation
- **Benefits**: Easy to switch between different storage backends

### 2. Observer Pattern
- **Purpose**: Notifies UI of data changes
- **Implementation**: `LinkService` notifies observers when data changes
- **Benefits**: Automatic UI updates without tight coupling

### 3. Model-View-Controller (MVC)
- **Model**: `Link` entity and `LinkService` business logic
- **View**: UI components (`LinkListView`, `SearchBar`, dialogs)
- **Controller**: `LinkController` coordinates between model and view

### 4. Dependency Injection
- **Purpose**: Loose coupling between components
- **Implementation**: Dependencies are injected through constructors
- **Benefits**: Easy testing and component substitution

### 5. Factory Pattern (Implicit)
- **Purpose**: Creating different types of dialogs
- **Implementation**: Dialog classes with factory-like constructors
- **Benefits**: Consistent dialog creation and management

## Project Structure

```
├── models/
│   ├── __init__.py
│   └── link.py                 # Link entity with validation
├── repositories/
│   ├── __init__.py
│   └── link_repository.py      # Data access abstraction
├── services/
│   ├── __init__.py
│   ├── browser_service.py      # Browser operations
│   └── link_service.py         # Business logic
├── ui/
│   ├── __init__.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── link_list_view.py   # Link list display
│   │   └── search_bar.py       # Search functionality
│   └── dialogs/
│       ├── __init__.py
│       ├── edit_dialog.py      # Edit link dialog
│       └── add_links_dialog.py # Add links dialog
├── controllers/
│   ├── __init__.py
│   └── link_controller.py      # Main controller
├── utils/
│   ├── __init__.py
│   └── date_formatter.py       # Date formatting utilities
├── main_refactored.py          # New main application file
├── main.py                     # Original application (kept for reference)
└── README.md                   # This file
```

## Key Features

### Clean Architecture
- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Direction**: Dependencies point inward (toward business logic)
- **Testability**: Easy to unit test individual components

### Extensibility
- **New Storage Backends**: Implement `LinkRepository` interface
- **New Browser Types**: Implement `BrowserService` interface
- **New UI Components**: Add to UI layer without affecting business logic

### Maintainability
- **Single Responsibility**: Each class has one reason to change
- **Clear Interfaces**: Well-defined contracts between components
- **Consistent Patterns**: Similar problems solved in similar ways

## Usage

### Running the Application

```bash
# Run the refactored version
python main_refactored.py

# Run the original version (for comparison)
python main.py
```

### Key Functionality
- **Add Links**: Batch add multiple URLs
- **Edit Links**: Modify link properties with validation
- **Search**: Real-time search through links
- **Sort**: Click column headers to sort
- **Favorites**: Mark important links
- **Read/Unread**: Track which links have been opened
- **Random**: Open random links or random unread links

### Keyboard Shortcuts
- **Ctrl/Cmd + F**: Focus search
- **Escape**: Clear search (when search is focused) or deselect all (when list is focused)
- **Ctrl/Cmd + D**: Toggle favorite status of selected links
- **Ctrl/Cmd + E**: Toggle read/unread status of selected links
- **Ctrl/Cmd + R**: Open random link
- **Space**: Open random unread link
- **Enter**: Edit selected link
- **Double-click**: Open links
- **Backspace**: Delete selected links

## Testing Strategy

The refactored architecture makes testing much easier:

```python
# Example: Testing the LinkService
def test_add_link():
    # Arrange
    mock_repository = Mock(spec=LinkRepository)
    mock_browser = Mock(spec=BrowserService)
    service = LinkService(mock_repository, mock_browser)
    
    # Act
    service.add_link("Test", "https://example.com")
    
    # Assert
    mock_repository.add.assert_called_once()
```

## Future Enhancements
- **Database Storage**: Implement `DatabaseLinkRepository`
- **Cloud Sync**: Add cloud synchronization service
- **Import/Export**: Add various format importers/exporters
- **Themes**: Add theming support to UI components
- **Plugins**: Plugin system for extensibility
- **REST API**: Add API service for remote access