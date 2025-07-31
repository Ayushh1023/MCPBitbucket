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
    max_items: Optional[int] = Field(None, description="Maximum number of files/directories to return (for pagination)")

class CodebasePaginationRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    branch: str = Field("main", description="Branch name")
    path: str = Field("", description="Path within the repository")
    max_items: int = Field(10, description="Maximum number of files/directories to return")

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

class PullRequestRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    state: str = Field("OPEN", description="PR state: OPEN, MERGED, DECLINED, SUPERSEDED")
    page_size: int = Field(50, description="Number of PRs per page")

class PullRequestFilesRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")
    pr_id: int = Field(..., description="Pull Request ID")

class BranchRequest(BaseModel):
    workspace: str = Field(..., description="Workspace slug")
    repo_slug: str = Field(..., description="Repository slug")

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

def _get_workspaces_internal() -> Dict[str, Any]:
    """
    Internal function to get workspaces (not an MCP tool)
    Used by other functions to fetch workspaces
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

def _get_repositories_from_workspace_internal(workspace: str, page_size: int = 50) -> Dict[str, Any]:
    """
    Internal function to get repositories from a specific workspace (not an MCP tool)
    Used by other functions to fetch repositories
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
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
        
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
                    "error": f"Failed to get repositories from workspace {workspace}: {response.status_code}",
                    "details": response.text
                }
        
        return {
            "success": True,
            "workspace": workspace,
            "repositories": all_repos,
            "count": len(all_repos)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting repositories from workspace {workspace}: {str(e)}"
        }

def _get_user_repositories_internal(page_size: int = 50) -> Dict[str, Any]:
    """
    Internal function to get user's repositories (not an MCP tool)
    Used by other functions to fetch user repositories
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
                    "error": f"Failed to get user repositories: {response.status_code}",
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
            "error": f"Exception while getting user repositories: {str(e)}"
        }

def _get_repository_branches_internal(workspace: str, repo_slug: str) -> Dict[str, Any]:
    """
    Internal function to get branches from a repository (not an MCP tool)
    Used by other functions to fetch repository branches
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
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/refs/branches"
        
        params = {
            "pagelen": 100,  # Get up to 100 branches
            "sort": "-name"  # Sort by name descending
        }
        
        all_branches = []
        next_url = url
        
        while next_url:
            response = requests.get(next_url, headers=auth_headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                branches = data.get('values', [])
                all_branches.extend(branches)
                
                next_url = data.get('next')
                params = {}  # Clear params for subsequent requests
            else:
                return {
                    "success": False,
                    "error": f"Failed to get branches: {response.status_code}",
                    "details": response.text
                }
        
        # Process branches to extract useful information
        processed_branches = []
        default_branch = None
        
        for branch in all_branches:
            branch_info = {
                'name': branch.get('name', 'Unknown'),
                'hash': branch.get('target', {}).get('hash', 'Unknown'),
                'short_hash': branch.get('target', {}).get('hash', 'Unknown')[:8],
                'author': branch.get('target', {}).get('author', {}).get('raw', 'Unknown'),
                'date': branch.get('target', {}).get('date', 'Unknown'),
                'message': branch.get('target', {}).get('message', 'Unknown')
            }
            processed_branches.append(branch_info)
            
            # Identify default branch (main, master, develop, or first one)
            if branch_info['name'] in ['main', 'master', 'develop']:
                default_branch = branch_info['name']
        
        # If no default branch found, use the first one
        if not default_branch and processed_branches:
            default_branch = processed_branches[0]['name']
        
        return {
            "success": True,
            "workspace": workspace,
            "repository": repo_slug,
            "branches": processed_branches,
            "default_branch": default_branch,
            "count": len(processed_branches)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting branches: {str(e)}"
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
    # Use the internal workspaces function
    result = _get_workspaces_internal()
    return result

@mcp.tool(name="get_repositories", description="Get list of repositories from a workspace or user account")
async def get_repositories(workspace: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
    """
    Get list of repositories
    
    Args:
        workspace: Workspace slug (optional, if not provided gets repositories from all workspaces)
        page_size: Number of repositories per page
    
    Returns:
        List of repositories
    """
    if workspace:
        # Get repositories from specific workspace
        result = _get_repositories_from_workspace_internal(workspace, page_size)
        return result
    else:
        # Get repositories from all workspaces
        workspaces_result = _get_workspaces_internal()
        if not workspaces_result.get("success"):
            return workspaces_result
        
        workspaces = workspaces_result.get("workspaces", [])
        all_repositories = []
        workspace_repos_map = {}
        
        for workspace_info in workspaces:
            workspace_slug = workspace_info.get('slug')
            repos_result = _get_repositories_from_workspace_internal(workspace_slug, page_size)
            
            if repos_result.get("success"):
                repos = repos_result.get("repositories", [])
                all_repositories.extend(repos)
                workspace_repos_map[workspace_slug] = {
                    "workspace_name": workspace_info.get('name'),
                    "repositories": repos,
                    "count": len(repos)
                }
            else:
                # Log error but continue with other workspaces
                print(f"Warning: Failed to get repositories from workspace {workspace_slug}: {repos_result.get('error')}")
        
        return {
            "success": True,
            "repositories": all_repositories,
            "total_count": len(all_repositories),
            "workspaces_processed": len(workspaces),
            "workspace_details": workspace_repos_map
        }

@mcp.tool(name="get_all_repositories_with_workspaces", description="Get repositories from all workspaces with detailed workspace information")
async def get_all_repositories_with_workspaces(page_size: int = 50) -> Dict[str, Any]:
    """
    Get repositories from all workspaces with detailed workspace information
    
    Args:
        page_size: Number of repositories per page per workspace
    
    Returns:
        Detailed information about repositories organized by workspaces
    """
    # Get workspaces first
    workspaces_result = _get_workspaces_internal()
    if not workspaces_result.get("success"):
        return workspaces_result
    
    workspaces = workspaces_result.get("workspaces", [])
    all_repositories = []
    workspace_repos_map = {}
    
    for workspace_info in workspaces:
        workspace_slug = workspace_info.get('slug')
        repos_result = _get_repositories_from_workspace_internal(workspace_slug, page_size)
        
        if repos_result.get("success"):
            repos = repos_result.get("repositories", [])
            all_repositories.extend(repos)
            workspace_repos_map[workspace_slug] = {
                "workspace_name": workspace_info.get('name'),
                "repositories": repos,
                "count": len(repos)
            }
        else:
            # Log error but continue with other workspaces
            print(f"Warning: Failed to get repositories from workspace {workspace_slug}: {repos_result.get('error')}")
    
    return {
        "success": True,
        "repositories": all_repositories,
        "total_count": len(all_repositories),
        "workspaces_processed": len(workspaces),
        "workspace_details": workspace_repos_map
    }

@mcp.tool(name="get_repository_branches", description="Get list of branches from a repository")
async def get_repository_branches(workspace: str, repo_slug: str) -> Dict[str, Any]:
    """
    Get list of branches from a repository
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
    
    Returns:
        List of branches with details and default branch information
    """
    # Use the internal branches function
    result = _get_repository_branches_internal(workspace, repo_slug)
    return result

def _get_repository_codebase_internal(workspace: str, repo_slug: str, branch: str = "main", path: str = "", max_items: Optional[int] = None) -> Dict[str, Any]:
    """
    Internal function to get the codebase structure and contents of a repository (not an MCP tool)
    Used by other functions to fetch codebase structure
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
    
    # Global counters for pagination
    total_items_count = 0
    files_count = 0
    directories_count = 0
    
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
        nonlocal total_items_count, files_count, directories_count
        
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
                    # Check if we've reached the max_items limit
                    if max_items is not None and total_items_count >= max_items:
                        break
                    
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
                        total_items_count += 1
                        files_count += 1
                    elif item_type == 'commit_directory':
                        # It's a directory, recurse
                        sub_structure = get_directory_structure(item_path)
                        if sub_structure:
                            structure['children'].append(sub_structure)
                            total_items_count += 1
                            directories_count += 1
                
                return structure
            else:
                return None
                
        except Exception as e:
            return None
    
    try:
        structure = get_directory_structure(path)
        if structure:
            # Add statistics to the response
            structure['files_count'] = files_count
            structure['directories_count'] = directories_count
            structure['total_items'] = total_items_count
            
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

@mcp.tool(name="get_repository_codebase", description="Get the complete codebase structure and contents of a repository")
async def get_repository_codebase(workspace: str, repo_slug: str, branch: str = "main", path: str = "", max_items: Optional[int] = None) -> Dict[str, Any]:
    """
    Get the codebase structure and contents of a repository
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
        max_items: Maximum number of files/directories to return (for pagination)
    
    Returns:
        Repository structure with file contents or list of available branches if no branch specified
    """
    # If no branch is specified or it's the default "main", first check available branches
    if branch == "main":
        branches_result = _get_repository_branches_internal(workspace, repo_slug)
        if branches_result.get("success"):
            branches = branches_result.get("branches", [])
            default_branch = branches_result.get("default_branch", "main")
            
            # If there are multiple branches, return the branch list instead of codebase
            if len(branches) > 1:
                return {
                    "success": True,
                    "message": f"Multiple branches found. Please specify a branch name. Available branches: {[b['name'] for b in branches]}",
                    "workspace": workspace,
                    "repository": repo_slug,
                    "available_branches": branches,
                    "default_branch": default_branch,
                    "branch_count": len(branches),
                    "suggestion": f"Use branch '{default_branch}' or specify another branch from the list"
                }
            else:
                # Only one branch, use it
                branch = branches[0]['name'] if branches else "main"
    
    # Use the internal codebase function
    result = _get_repository_codebase_internal(workspace, repo_slug, branch, path, max_items)
    return result

@mcp.tool(name="get_repository_codebase_paginated", description="Get a limited number of files/directories from a repository codebase")
async def get_repository_codebase_paginated(workspace: str, repo_slug: str, max_items: int = 10, branch: str = "main", path: str = "") -> Dict[str, Any]:
    """
    Get a limited number of files/directories from a repository codebase (paginated)
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        max_items: Maximum number of files/directories to return (required for pagination)
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
    
    Returns:
        Repository structure with limited file contents or list of available branches if no branch specified
    """
    # If no branch is specified or it's the default "main", first check available branches
    if branch == "main":
        branches_result = _get_repository_branches_internal(workspace, repo_slug)
        if branches_result.get("success"):
            branches = branches_result.get("branches", [])
            default_branch = branches_result.get("default_branch", "main")
            
            # If there are multiple branches, return the branch list instead of codebase
            if len(branches) > 1:
                return {
                    "success": True,
                    "message": f"Multiple branches found. Please specify a branch name. Available branches: {[b['name'] for b in branches]}",
                    "workspace": workspace,
                    "repository": repo_slug,
                    "available_branches": branches,
                    "default_branch": default_branch,
                    "branch_count": len(branches),
                    "suggestion": f"Use branch '{default_branch}' or specify another branch from the list"
                }
            else:
                # Only one branch, use it
                branch = branches[0]['name'] if branches else "main"
    
    # Use the internal codebase function with pagination
    result = _get_repository_codebase_internal(workspace, repo_slug, branch, path, max_items)
    return result

def _get_specific_file_content_internal(workspace: str, repo_slug: str, file_path: str, branch: str = "main") -> Dict[str, Any]:
    """
    Internal function to get the content of a specific file (not an MCP tool)
    Used by other functions to fetch file content
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
    # Use the internal file content function
    result = _get_specific_file_content_internal(workspace, repo_slug, file_path, branch)
    return result

def _get_repository_files_list_internal(workspace: str, repo_slug: str, branch: str = "main", path: str = "") -> Dict[str, Any]:
    """
    Internal function to get a list of all files in a repository (not an MCP tool)
    Used by other functions to fetch file lists
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

def _get_pull_requests_internal(workspace: str, repo_slug: str, state: str = "OPEN", page_size: int = 50) -> Dict[str, Any]:
    """
    Internal function to get pull requests from a repository (not an MCP tool)
    Used by other functions to fetch pull requests
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
        base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests"
        
        params = {
            "pagelen": page_size,
            "state": state.upper(),
            "sort": "-updated_on"
        }
        
        all_prs = []
        next_url = base_url
        
        while next_url:
            response = requests.get(next_url, headers=auth_headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                prs = data.get('values', [])
                all_prs.extend(prs)
                
                next_url = data.get('next')
                params = {}  # Clear params for subsequent requests
            else:
                return {
                    "success": False,
                    "error": f"Failed to get pull requests: {response.status_code}",
                    "details": response.text
                }
        
        return {
            "success": True,
            "workspace": workspace,
            "repository": repo_slug,
            "state": state.upper(),
            "pull_requests": all_prs,
            "count": len(all_prs)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting pull requests: {str(e)}"
        }

def _get_pull_request_files_internal(workspace: str, repo_slug: str, pr_id: int) -> Dict[str, Any]:
    """
    Internal function to get files changed in a pull request (not an MCP tool)
    Used by other functions to fetch PR file changes
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
        base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/diffstat"
        
        response = requests.get(base_url, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            files = data.get('values', [])
            
            # Categorize files by change type
            added_files = []
            modified_files = []
            deleted_files = []
            renamed_files = []
            
            for file_info in files:
                file_path = file_info.get('new', {}).get('path') or file_info.get('old', {}).get('path')
                change_type = file_info.get('status', 'unknown')
                
                file_data = {
                    'path': file_path,
                    'status': change_type,
                    'lines_added': file_info.get('lines_added', 0),
                    'lines_removed': file_info.get('lines_removed', 0),
                    'old_path': file_info.get('old', {}).get('path'),
                    'new_path': file_info.get('new', {}).get('path')
                }
                
                if change_type == 'added':
                    added_files.append(file_data)
                elif change_type == 'modified':
                    modified_files.append(file_data)
                elif change_type == 'removed':
                    deleted_files.append(file_data)
                elif change_type == 'renamed':
                    renamed_files.append(file_data)
            
            return {
                "success": True,
                "workspace": workspace,
                "repository": repo_slug,
                "pr_id": pr_id,
                "files": files,
                "summary": {
                    "total_files": len(files),
                    "added_files": len(added_files),
                    "modified_files": len(modified_files),
                    "deleted_files": len(deleted_files),
                    "renamed_files": len(renamed_files)
                },
                "categorized_files": {
                    "added": added_files,
                    "modified": modified_files,
                    "deleted": deleted_files,
                    "renamed": renamed_files
                }
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get pull request files: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception while getting pull request files: {str(e)}"
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
    # Use the internal files list function
    result = _get_repository_files_list_internal(workspace, repo_slug, branch, path)
    return result

@mcp.tool(name="get_pull_requests", description="Get pull requests from a repository")
async def get_pull_requests(workspace: str, repo_slug: str, state: str = "OPEN", page_size: int = 50) -> Dict[str, Any]:
    """
    Get pull requests from a repository
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        state: PR state (OPEN, MERGED, DECLINED, SUPERSEDED) - default: OPEN
        page_size: Number of PRs per page (default: 50)
    
    Returns:
        List of pull requests with details
    """
    # Use the internal pull requests function
    result = _get_pull_requests_internal(workspace, repo_slug, state, page_size)
    return result

@mcp.tool(name="get_pull_request_files", description="Get files changed in a pull request")
async def get_pull_request_files(workspace: str, repo_slug: str, pr_id: int) -> Dict[str, Any]:
    """
    Get files changed in a pull request
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        pr_id: Pull Request ID
    
    Returns:
        List of files changed in the PR with change details
    """
    # Use the internal pull request files function
    result = _get_pull_request_files_internal(workspace, repo_slug, pr_id)
    return result

@mcp.tool(name="save_codebase_to_file", description="Save the repository codebase structure to a JSON file")
async def save_codebase_to_file(workspace: str, repo_slug: str, filename: str, branch: str = "main", path: str = "", max_items: Optional[int] = None) -> Dict[str, Any]:
    """
    Save the codebase structure to a JSON file
    
    Args:
        workspace: Workspace name/slug
        repo_slug: Repository slug
        filename: Local filename to save to
        branch: Branch name (default: 'main')
        path: Path within the repository (default: root)
        max_items: Maximum number of files/directories to save (for pagination)
    
    Returns:
        Success status and file information
    """
    # Use the internal codebase function to get structure
    codebase_result = _get_repository_codebase_internal(workspace, repo_slug, branch, path, max_items)
    
    if not codebase_result.get("success"):
        return codebase_result
    
    try:
        structure = codebase_result.get("structure")
        
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