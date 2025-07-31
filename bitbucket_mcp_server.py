import asyncio
import base64
import json
import os
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("bitbucket-server")

# Your Bitbucket personal access token or app password
BITBUCKET_TOKEN = os.getenv("BITBUCKET_TOKEN", "")

# Bitbucket email (can be configured via environment variable or MCP config)
BITBUCKET_EMAIL = os.getenv("BITBUCKET_EMAIL", "")

# Pydantic models for request/response
class AuthRequest(BaseModel):
    email: str = Field(..., description="Bitbucket email address")

class RepositoryRequest(BaseModel):
    workspace: Optional[str] = Field(None, description="Workspace slug (optional)")
    page_size: int = Field(50, description="Number of repositories per page")

class CodebaseRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    branch: str = Field("main", description="Branch name")
    path: str = Field("", description="Path within the repository")

class FileContentRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    file_path: str = Field(..., description="Path to the file within the repository")
    branch: str = Field("main", description="Branch name")

class FilesListRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    branch: str = Field("main", description="Branch name")
    path: str = Field("", description="Path within the repository")

# Global variable to store authentication headers
auth_headers = None

def get_headers_with_email(email: str) -> Dict[str, str]:
    """Create authentication headers with email and token"""
    credentials = f"{email}:{BITBUCKET_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_credentials}"
    }

def _authenticate_internal(email: str = None) -> Dict[str, Any]:
    """
    Internal authentication function (not an MCP tool)
    Used by other functions to authenticate automatically
    """
    global auth_headers
    
    # Use provided email or fall back to configured email
    if email is None:
        if BITBUCKET_EMAIL:
            email = BITBUCKET_EMAIL
        else:
            return {
                "success": False,
                "error": "No email provided and BITBUCKET_EMAIL not configured."
            }
    
    try:
        headers = get_headers_with_email(email)
        response = requests.get(
            "https://api.bitbucket.org/2.0/user",
            headers=headers
        )
        
        if response.status_code == 200:
            user_data = response.json()
            auth_headers = headers  # Store for future use
            return {
                "success": True,
                "user": user_data,
                "message": f"Authenticated as: {user_data['username']} using email: {email}"
            }
        else:
            return {
                "success": False,
                "error": f"Authentication failed: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception during authentication: {str(e)}"
        }

@mcp.tool(name="authenticate_user", description="Authenticate with Bitbucket using email and token")
async def authenticate_user(email: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticate with Bitbucket using email and token
    
    Args:
        email: Your Bitbucket email address (optional, will use config if not provided)
    
    Returns:
        User information if authentication successful
    """
    # Use the internal authentication function
    result = _authenticate_internal(email)
    return result

@mcp.tool(name="get_workspaces", description="Get list of workspaces the user has access to")
async def get_workspaces() -> Dict[str, Any]:
    """
    Get list of workspaces the user has access to
    
    Returns:
        List of workspaces
    """
    global auth_headers
    
    if not auth_headers:
        # Try to authenticate automatically if email is configured
        if BITBUCKET_EMAIL:
            auth_result = _authenticate_internal()
            if not auth_result.get("success"):
                return auth_result
        else:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first using authenticate_user() or configure BITBUCKET_EMAIL."
            }
    
    try:
        response = requests.get(
            "https://api.bitbucket.org/2.0/workspaces",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            workspaces = data.get('values', [])
            return {
                "success": True,
                "workspaces": workspaces,
                "count": len(workspaces)
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get workspaces: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting workspaces: {str(e)}"
        }

@mcp.tool(name="get_repositories", description="Get list of repositories from a workspace or user account")
async def get_repositories(workspace: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
    """
    Get list of repositories
    
    Args:
        workspace: Workspace slug (optional, if not provided gets user's repositories)
        page_size: Number of repositories per page
    
    Returns:
        List of repositories
    """
    global auth_headers
    
    if not auth_headers:
        # Try to authenticate automatically if email is configured
        if BITBUCKET_EMAIL:
            auth_result = _authenticate_internal()
            if not auth_result.get("success"):
                return auth_result
        else:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first using authenticate_user() or configure BITBUCKET_EMAIL."
            }
    
    try:
        if workspace:
            url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
        else:
            url = "https://api.bitbucket.org/2.0/repositories"
        
        params = {
            "pagelen": page_size,
            "sort": "-updated_on"
        }
        
        all_repos = []
        next_url = url
        
        while next_url:
            response = requests.get(next_url, headers=auth_headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                repos = data.get('values', [])
                all_repos.extend(repos)
                
                next_url = data.get('next')
                params = {}  # Clear params for subsequent requests
            else:
                return {
                    "success": False,
                    "error": f"Failed to get repositories: {response.status_code}",
                    "details": response.text
                }
        
        return {
            "success": True,
            "repositories": all_repos,
            "count": len(all_repos)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting repositories: {str(e)}"
        }

@mcp.tool(name="get_repository_codebase", description="Get the complete codebase structure and contents of a repository")
async def get_repository_codebase(workspace: str, repo_slug: str, branch: str = "main", path: str = "") -> Dict[str, Any]:
    """
    Get the codebase structure and contents of a repository
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
    
    Returns:
        Repository structure with file contents
    """
    global auth_headers
    
    if not auth_headers:
        return {
            "success": False,
            "error": "Not authenticated. Please authenticate first."
        }
    
    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
    
    def get_file_contents(file_path: str) -> str:
        """Get contents of a specific file"""
        try:
            response = requests.get(
                f"{base_url}/src/{branch}/{file_path}",
                headers=auth_headers
            )
            if response.status_code == 200:
                return response.text
            else:
                return f"Error: Could not fetch file {file_path} (Status: {response.status_code})"
        except Exception as e:
            return f"Error: Exception while fetching {file_path}: {str(e)}"
    
    def get_directory_structure(dir_path: str = '') -> Optional[Dict[str, Any]]:
        """Recursively get directory structure"""
        try:
            response = requests.get(
                f"{base_url}/src/{branch}/{dir_path}",
                headers=auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                structure = {
                    'type': 'directory',
                    'path': dir_path,
                    'children': []
                }
                
                for item in data.get('values', []):
                    item_type = item.get('type', 'unknown')
                    item_path = item.get('path', '')
                    
                    if item_type == 'commit_file':
                        # It's a file
                        file_info = {
                            'type': 'file',
                            'path': item_path,
                            'size': item.get('size', 0),
                            'content': get_file_contents(item_path) if item_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.html', '.css', '.json', '.xml', '.md', '.txt', '.yml', '.yaml', '.sh', '.bat', '.ps1')) else None
                        }
                        structure['children'].append(file_info)
                    elif item_type == 'commit_directory':
                        # It's a directory, recurse
                        sub_structure = get_directory_structure(item_path)
                        if sub_structure:
                            structure['children'].append(sub_structure)
                
                return structure
            else:
                return None
                
        except Exception as e:
            return None
    
    try:
        structure = get_directory_structure(path)
        if structure:
            return {
                "success": True,
                "workspace": workspace,
                "repository": repo_slug,
                "branch": branch,
                "structure": structure
            }
        else:
            return {
                "success": False,
                "error": "Failed to get codebase structure"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting codebase: {str(e)}"
        }

@mcp.tool(name="get_specific_file_content", description="Get the content of a specific file from a repository")
async def get_specific_file_content(workspace: str, repo_slug: str, file_path: str, branch: str = "main") -> Dict[str, Any]:
    """
    Get the content of a specific file from a repository
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        file_path: Path to the file within the repository
        branch: Branch name (default: 'main')
    
    Returns:
        File content or error message
    """
    global auth_headers
    
    if not auth_headers:
        # Try to authenticate automatically if email is configured
        if BITBUCKET_EMAIL:
            auth_result = _authenticate_internal()
            if not auth_result.get("success"):
                return auth_result
        else:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first using authenticate_user() or configure BITBUCKET_EMAIL."
            }
    
    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
    
    try:
        response = requests.get(
            f"{base_url}/src/{branch}/{file_path}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "workspace": workspace,
                "repository": repo_slug,
                "file_path": file_path,
                "branch": branch,
                "content": response.text,
                "size": len(response.text)
            }
        else:
            return {
                "success": False,
                "error": f"Could not fetch file {file_path} (Status: {response.status_code})"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while fetching {file_path}: {str(e)}"
        }

@mcp.tool(name="get_repository_files_list", description="Get a list of all files in a repository without content")
async def get_repository_files_list(workspace: str, repo_slug: str, branch: str = "main", path: str = "") -> Dict[str, Any]:
    """
    Get a list of all files in a repository (without content)
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
    
    Returns:
        List of file paths
    """
    global auth_headers
    
    if not auth_headers:
        # Try to authenticate automatically if email is configured
        if BITBUCKET_EMAIL:
            auth_result = _authenticate_internal()
            if not auth_result.get("success"):
                return auth_result
        else:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first using authenticate_user() or configure BITBUCKET_EMAIL."
            }
    
    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
    all_files = []
    
    def get_files_recursive(dir_path: str = ''):
        """Recursively get all files in directory"""
        try:
            response = requests.get(
                f"{base_url}/src/{branch}/{dir_path}",
                headers=auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('values', []):
                    item_type = item.get('type', 'unknown')
                    item_path = item.get('path', '')
                    
                    if item_type == 'commit_file':
                        # It's a file
                        all_files.append(item_path)
                    elif item_type == 'commit_directory':
                        # It's a directory, recurse
                        get_files_recursive(item_path)
            else:
                return False
                
        except Exception as e:
            return False
    
    try:
        success = get_files_recursive(path)
        if success is False:
            return {
                "success": False,
                "error": "Failed to get files list"
            }
        
        # Filter code files
        code_extensions = ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.html', '.css', '.json', '.xml', '.md', '.txt', '.yml', '.yaml', '.sh', '.bat', '.ps1', '.dart', '.kt', '.swift', '.rb', '.php', '.go', '.rs', '.cs', '.vb', '.sql')
        code_files = [f for f in all_files if f.lower().endswith(code_extensions)]
        
        return {
            "success": True,
            "workspace": workspace,
            "repository": repo_slug,
            "branch": branch,
            "all_files": all_files,
            "code_files": code_files,
            "total_files": len(all_files),
            "code_files_count": len(code_files)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting files list: {str(e)}"
        }

@mcp.tool(name="save_codebase_to_file", description="Save the repository codebase structure to a JSON file")
async def save_codebase_to_file(workspace: str, repo_slug: str, filename: str, branch: str = "main", path: str = "") -> Dict[str, Any]:
    """
    Save the codebase structure to a JSON file
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        filename: Local filename to save to
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
    
    Returns:
        Success status and file information
    """
    global auth_headers
    
    if not auth_headers:
        # Try to authenticate automatically if email is configured
        if BITBUCKET_EMAIL:
            auth_result = _authenticate_internal()
            if not auth_result.get("success"):
                return auth_result
        else:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first using authenticate_user() or configure BITBUCKET_EMAIL."
            }
    
    # Manually get the codebase structure (don't call another tool)
    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
    
    def get_file_contents(file_path: str) -> str:
        """Get contents of a specific file"""
        try:
            response = requests.get(
                f"{base_url}/src/{branch}/{file_path}",
                headers=auth_headers
            )
            if response.status_code == 200:
                return response.text
            else:
                return f"Error: Could not fetch file {file_path} (Status: {response.status_code})"
        except Exception as e:
            return f"Error: Exception while fetching {file_path}: {str(e)}"
    
    def get_directory_structure(dir_path: str = '') -> Optional[Dict[str, Any]]:
        """Recursively get directory structure"""
        try:
            response = requests.get(
                f"{base_url}/src/{branch}/{dir_path}",
                headers=auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                structure = {
                    'type': 'directory',
                    'path': dir_path,
                    'children': []
                }
                
                for item in data.get('values', []):
                    item_type = item.get('type', 'unknown')
                    item_path = item.get('path', '')
                    
                    if item_type == 'commit_file':
                        # It's a file
                        file_info = {
                            'type': 'file',
                            'path': item_path,
                            'size': item.get('size', 0),
                            'content': get_file_contents(item_path) if item_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.html', '.css', '.json', '.xml', '.md', '.txt', '.yml', '.yaml', '.sh', '.bat', '.ps1')) else None
                        }
                        structure['children'].append(file_info)
                    elif item_type == 'commit_directory':
                        # It's a directory, recurse
                        sub_structure = get_directory_structure(item_path)
                        if sub_structure:
                            structure['children'].append(sub_structure)
                
                return structure
            else:
                return None
                
        except Exception as e:
            return None
    
    try:
        structure = get_directory_structure(path)
        if not structure:
            return {
                "success": False,
                "error": "Failed to get codebase structure"
            }
        
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        output_data = {
            'workspace': workspace,
            'repository': repo_slug,
            'timestamp': timestamp,
            'structure': structure
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "filename": filename,
            "workspace": workspace,
            "repository": repo_slug,
            "message": f"Codebase structure saved to {filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error saving to file: {str(e)}"
        }

if __name__ == "__main__":
    # Run the server
    mcp.run() 