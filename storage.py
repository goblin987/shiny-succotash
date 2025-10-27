import json
import os
import uuid
from typing import Dict, List, Optional

CONFIG_FILE = 'config.json'

DEFAULT_CONFIG = {
    "welcome_message": "👋 Welcome to our community portal!\n\nPlease select a group below to get your invite link:",
    "groups": []
}

def load_config() -> Dict:
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict) -> bool:
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_welcome_message() -> str:
    """Get the current welcome message"""
    config = load_config()
    return config.get('welcome_message', DEFAULT_CONFIG['welcome_message'])

def update_welcome_message(message: str) -> bool:
    """Update the welcome message"""
    config = load_config()
    config['welcome_message'] = message
    return save_config(config)

def get_groups() -> List[Dict]:
    """Get all groups"""
    config = load_config()
    return config.get('groups', [])

def get_group_by_id(group_id: str) -> Optional[Dict]:
    """Get a specific group by ID"""
    groups = get_groups()
    for group in groups:
        if group.get('id') == group_id:
            return group
    return None

def add_group(name: str, chat_id: str) -> Dict:
    """Add a new group"""
    config = load_config()
    
    new_group = {
        'id': str(uuid.uuid4()),
        'name': name,
        'chat_id': chat_id
    }
    
    config['groups'].append(new_group)
    save_config(config)
    return new_group

def delete_group(group_id: str) -> bool:
    """Delete a group by ID"""
    config = load_config()
    groups = config.get('groups', [])
    
    # Filter out the group to delete
    new_groups = [g for g in groups if g.get('id') != group_id]
    
    if len(new_groups) == len(groups):
        return False  # Group not found
    
    config['groups'] = new_groups
    return save_config(config)

def group_exists(chat_id: str) -> bool:
    """Check if a group with the given chat_id already exists"""
    groups = get_groups()
    return any(g.get('chat_id') == chat_id for g in groups)

