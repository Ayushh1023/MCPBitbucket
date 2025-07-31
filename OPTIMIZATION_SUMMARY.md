# Bitbucket MCP Server Optimization Summary

## Overview

The Bitbucket MCP Server has been optimized to address the following key issues:

1. **Tool-to-Tool Calls**: MCP tools cannot call other tools internally
2. **Repository Fetching**: Need to fetch repositories from all workspaces when no specific workspace is provided
3. **Code Duplication**: Common functionality was duplicated across multiple tools
4. **Authentication Flow**: Inconsistent authentication handling across tools

## Key Optimizations Implemented

### 1. Internal Function Architecture

Created separate internal functions for all core functionality:

#### Authentication
- **`_authenticate_internal()`**: Centralized authentication logic
- **`get_headers_with_email()`**: Reusable header generation

#### Workspace Management
- **`_get_workspaces_internal()`**: Internal workspace fetching
- **`_get_repositories_from_workspace_internal()`**: Repository fetching from specific workspace
- **`_get_user_repositories_internal()`**: User repository fetching

#### Repository Operations
- **`_get_repository_codebase_internal()`**: Codebase structure fetching
- **`_get_specific_file_content_internal()`**: File content fetching
- **`_get_repository_files_list_internal()`**: File list fetching

#### Pull Request Operations
- **`_get_pull_requests_internal()`**: Pull request fetching
- **`_get_pull_request_files_internal()`**: Pull request file changes fetching

### 2. Enhanced Repository Fetching

#### Before Optimization
```python
# get_repositories() only fetched from user account or specific workspace
if workspace:
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
else:
    url = "https://api.bitbucket.org/2.0/repositories"  # Only user repos
```

#### After Optimization
```python
# get_repositories() now fetches from all workspaces when no workspace specified
if workspace:
    # Get repositories from specific workspace
    result = _get_repositories_from_workspace_internal(workspace, page_size)
else:
    # Get repositories from all workspaces
    workspaces_result = _get_workspaces_internal()
    # ... fetch from each workspace and combine results
```

### 3. New Tool: `get_all_repositories_with_workspaces`

Added a dedicated tool for fetching repositories from all workspaces with detailed workspace information:

```python
@mcp.tool(name="get_all_repositories_with_workspaces")
async def get_all_repositories_with_workspaces(page_size: int = 50):
    # Returns detailed information about repositories organized by workspaces
```

### 4. New Pull Request Tools

Added comprehensive pull request functionality:

#### `get_pull_requests`
Fetches pull requests from a repository with filtering by state:

```python
@mcp.tool(name="get_pull_requests")
async def get_pull_requests(workspace: str, repo_slug: str, state: str = "OPEN", page_size: int = 50):
    # Returns pull requests with filtering by state (OPEN, MERGED, DECLINED, SUPERSEDED)
```

#### `get_pull_request_files`
Fetches and categorizes files changed in a pull request:

```python
@mcp.tool(name="get_pull_request_files")
async def get_pull_request_files(workspace: str, repo_slug: str, pr_id: int):
    # Returns categorized file changes (added, modified, deleted, renamed) with line counts
```

### 5. Codebase Pagination Support

Added pagination support for codebase fetching to handle large repositories efficiently:

#### Enhanced `get_repository_codebase`
```python
@mcp.tool(name="get_repository_codebase")
async def get_repository_codebase(workspace: str, repo_slug: str, branch: str = "main", path: str = "", max_items: Optional[int] = None):
    # Now supports optional max_items parameter for pagination
```

#### New `get_repository_codebase_paginated`
```python
@mcp.tool(name="get_repository_codebase_paginated")
async def get_repository_codebase_paginated(workspace: str, repo_slug: str, max_items: int = 10, branch: str = "main", path: str = ""):
    # Dedicated tool for paginated codebase access
```

#### Enhanced `save_codebase_to_file`
```python
@mcp.tool(name="save_codebase_to_file")
async def save_codebase_to_file(workspace: str, repo_slug: str, filename: str, branch: str = "main", path: str = "", max_items: Optional[int] = None):
    # Now supports max_items parameter for saving limited codebase structures
```

#### Internal Implementation
The `_get_repository_codebase_internal` function now supports pagination:

```python
def _get_repository_codebase_internal(workspace: str, repo_slug: str, branch: str = "main", path: str = "", max_items: Optional[int] = None):
    # Limits the number of files/directories returned based on max_items parameter
    # Stops processing when the limit is reached
```

### 6. Consistent Authentication Flow

All internal functions now handle authentication consistently:

```python
if not auth_headers:
    # Try to authenticate automatically if email is configured
    if BITBUCKET_EMAIL:
        auth_result = _authenticate_internal()
        if not auth_result.get("success"):
            return auth_result
    else:
        return {
            "success": False,
            "error": "Not authenticated. Please authenticate first..."
        }
```

## Benefits Achieved

### 1. **No Tool-to-Tool Calls**
- All MCP tools now use internal functions instead of calling other tools
- Prevents MCP protocol violations
- Enables proper tool isolation

### 2. **Code Reuse**
- Common functionality is shared through internal functions
- Reduced code duplication
- Easier maintenance and updates

### 3. **Enhanced Functionality**
- `get_repositories()` now fetches from all workspaces by default
- Better error handling and recovery
- More detailed response information

### 4. **Enhanced Functionality**
- `get_repositories()` now fetches from all workspaces by default
- Better error handling and recovery
- More detailed response information
- **Pull Request Management**: Complete PR workflow support with file change analysis
- **Codebase Pagination**: Support for limiting files/directories to improve performance

### 5. **Improved User Experience**
- Automatic authentication when credentials are configured
- Consistent error messages across all tools
- Better workspace and repository organization
- Comprehensive PR analysis with categorized file changes
- **Performance Optimization**: Pagination support for large repositories

## File Structure Changes

### Modified Files
- `bitbucket_mcp_server.py`: Main server with optimizations
- `README.md`: Updated documentation
- `test_optimized_server.py`: New test script

### New Internal Functions Added
1. `_get_workspaces_internal()`
2. `_get_repositories_from_workspace_internal()`
3. `_get_user_repositories_internal()`
4. `_get_repository_codebase_internal()`
5. `_get_specific_file_content_internal()`
6. `_get_repository_files_list_internal()`
7. `_get_pull_requests_internal()`
8. `_get_pull_request_files_internal()`

### New MCP Tools Added
1. `get_all_repositories_with_workspaces`
2. `get_pull_requests`
3. `get_pull_request_files`
4. `get_repository_codebase_paginated`

## Testing

The optimizations can be tested using:

```bash
python test_optimized_server.py
```

This test script verifies:
- Fetching repositories from all workspaces
- Comparing results between different methods
- Verifying internal function architecture
- Testing authentication flow
- Testing pull request functionality and file change analysis

### Codebase Pagination Testing

Test the new pagination functionality:

```bash
python test_codebase_pagination.py
```

This test script verifies:
- Pagination with different limits (5, 10, 20 items)
- Comparison between paginated and full codebase results
- Saving paginated codebase to files
- Performance benefits of limiting files/directories

## Backward Compatibility

All existing MCP tools maintain their original interfaces:
- `authenticate_user()`
- `get_workspaces()`
- `get_repositories()` (enhanced functionality)
- `get_repository_codebase()` (enhanced with pagination support)
- `get_specific_file_content()`
- `get_repository_files_list()`
- `get_pull_requests()` (new)
- `get_pull_request_files()` (new)
- `get_repository_codebase_paginated()` (new)
- `save_codebase_to_file()` (enhanced with pagination support)

The only change is that `get_repositories()` now fetches from all workspaces when no workspace is specified, providing more comprehensive results.

## Future Enhancements

The optimized architecture enables future enhancements:
- Caching mechanisms for frequently accessed data
- Batch operations for multiple repositories
- Advanced filtering and search capabilities
- Real-time repository monitoring
- Integration with other development tools 