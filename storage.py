import json
import os
import uuid
from typing import Dict, List, Optional

# Use persistent disk path on Render, fallback to local path for development
STORAGE_DIR = os.getenv('STORAGE_DIR', '/var/data')
CONFIG_FILE = os.path.join(STORAGE_DIR, 'config.json')

# Ensure storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "welcome_message": "👋 Welcome to our community portal!\n\nPlease select a group below to get your invite link:",
    "welcome_media": None,  # Stores file_id of photo or video
    "welcome_media_type": None,  # "photo" or "video"
    "groups": [],
    "referrals": {
        "users": {}  # user_id: {referral_count, referred_by, joined_at}
    }
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

def get_welcome_media() -> tuple:
    """Get the welcome media (file_id, media_type)"""
    config = load_config()
    return (config.get('welcome_media'), config.get('welcome_media_type'))

def update_welcome_media(file_id: str, media_type: str) -> bool:
    """Update the welcome media"""
    config = load_config()
    config['welcome_media'] = file_id
    config['welcome_media_type'] = media_type
    return save_config(config)

def remove_welcome_media() -> bool:
    """Remove the welcome media"""
    config = load_config()
    config['welcome_media'] = None
    config['welcome_media_type'] = None
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

def add_group(name: str, invite_link: str) -> Dict:
    """Add a new group with its invite link"""
    config = load_config()
    
    new_group = {
        'id': str(uuid.uuid4()),
        'name': name,
        'invite_link': invite_link
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

def group_exists(invite_link: str) -> bool:
    """Check if a group with the given invite_link already exists"""
    groups = get_groups()
    return any(g.get('invite_link') == invite_link for g in groups)

# ============================================
# Referral System Functions
# ============================================

def get_referral_data(user_id: str) -> Optional[Dict]:
    """Get referral data for a specific user"""
    config = load_config()
    referrals = config.get('referrals', {})
    users = referrals.get('users', {})
    return users.get(str(user_id))

def register_user(user_id: str, referred_by: Optional[str] = None) -> bool:
    """Register a new user or update existing user with referrer info"""
    from datetime import datetime
    
    config = load_config()
    
    # Ensure referrals structure exists
    if 'referrals' not in config:
        config['referrals'] = {'users': {}}
    if 'users' not in config['referrals']:
        config['referrals']['users'] = {}
    
    user_id_str = str(user_id)
    users = config['referrals']['users']
    
    # If user already exists, don't override their referrer
    if user_id_str in users:
        return False  # User already registered
    
    # Create new user entry (tracking joined groups)
    users[user_id_str] = {
        'referral_count': 0,
        'referred_by': str(referred_by) if referred_by else None,
        'joined_at': datetime.utcnow().isoformat(),
        'has_joined_group': False,  # Track if they've completed joining
        'groups_joined': []  # Track which groups they've joined
    }
    
    # Don't increment referral count yet - only when they join all required groups
    
    return save_config(config)

def mark_user_joined_group(user_id: str, group_id: str, total_groups: int) -> bool:
    """Mark that a user has clicked join for a group. Count referral only when all groups joined (if 3+)"""
    config = load_config()
    
    # Ensure referrals structure exists
    if 'referrals' not in config:
        config['referrals'] = {'users': {}}
    if 'users' not in config['referrals']:
        config['referrals']['users'] = {}
    
    user_id_str = str(user_id)
    users = config['referrals']['users']
    
    # If user doesn't exist, create them first
    if user_id_str not in users:
        from datetime import datetime
        users[user_id_str] = {
            'referral_count': 0,
            'referred_by': None,
            'joined_at': datetime.utcnow().isoformat(),
            'has_joined_group': False,
            'groups_joined': [group_id]
        }
    else:
        # Add group to joined list if not already there
        groups_joined = users[user_id_str].get('groups_joined', [])
        if group_id not in groups_joined:
            groups_joined.append(group_id)
            users[user_id_str]['groups_joined'] = groups_joined
    
    # Check if user has joined enough groups to count as referral
    groups_joined = users[user_id_str].get('groups_joined', [])
    
    # If already counted, don't count again
    if users[user_id_str].get('has_joined_group', False):
        return save_config(config)
    
    # Determine if referral should be counted
    # MUST join ALL groups, regardless of how many there are
    should_count = len(groups_joined) >= total_groups
    
    if should_count:
        # Mark user as having completed joining
        users[user_id_str]['has_joined_group'] = True
        
        # If this user was referred by someone, NOW increment their referral count
        referred_by = users[user_id_str].get('referred_by')
        if referred_by and str(referred_by) in users:
            users[str(referred_by)]['referral_count'] += 1
            save_config(config)
            return True  # Referral was counted
        elif referred_by:
            # Create the referrer entry if they don't exist yet
            from datetime import datetime
            users[str(referred_by)] = {
                'referral_count': 1,
                'referred_by': None,
                'joined_at': datetime.utcnow().isoformat(),
                'has_joined_group': False,
                'groups_joined': []
            }
            save_config(config)
            return True  # Referral was counted
    
    save_config(config)
    return False  # Not yet counted

def get_user_referral_count(user_id: str) -> int:
    """Get the number of users referred by this user"""
    data = get_referral_data(user_id)
    if not data:
        return 0
    return data.get('referral_count', 0)

def get_all_referral_stats() -> List[Dict]:
    """Get all users with their referral stats, sorted by referral count"""
    config = load_config()
    referrals = config.get('referrals', {})
    users = referrals.get('users', {})
    
    stats = []
    for user_id, data in users.items():
        stats.append({
            'user_id': user_id,
            'referral_count': data.get('referral_count', 0),
            'referred_by': data.get('referred_by'),
            'joined_at': data.get('joined_at')
        })
    
    # Sort by referral count (highest first)
    stats.sort(key=lambda x: x['referral_count'], reverse=True)
    return stats

def get_total_users() -> int:
    """Get total number of registered users"""
    config = load_config()
    referrals = config.get('referrals', {})
    users = referrals.get('users', {})
    return len(users)

def get_total_referrals() -> int:
    """Get total number of successful referrals (users who joined groups)"""
    config = load_config()
    referrals = config.get('referrals', {})
    users = referrals.get('users', {})
    
    total = 0
    for data in users.values():
        total += data.get('referral_count', 0)
    return total

def get_users_who_joined_groups() -> int:
    """Get count of users who have joined at least one group"""
    config = load_config()
    referrals = config.get('referrals', {})
    users = referrals.get('users', {})
    
    count = 0
    for data in users.values():
        if data.get('has_joined_group', False):
            count += 1
    return count

def reset_all_referral_counts() -> bool:
    """Reset referral counts for all users to 0 (for new competitions/weeks)"""
    config = load_config()
    
    if 'referrals' not in config or 'users' not in config['referrals']:
        return True  # Nothing to reset
    
    users = config['referrals']['users']
    
    # Reset all referral counts to 0
    for user_data in users.values():
        user_data['referral_count'] = 0
    
    return save_config(config)

