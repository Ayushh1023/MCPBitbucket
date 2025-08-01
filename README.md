# Bitbucket MCP Server

A Model Context Protocol (MCP) server built with FastMCP that provides access to Bitbucket repositories and codebases.

## Features

- **Authentication**: Secure authentication with Bitbucket using email and personal access token
- **Workspace Management**: List and access Bitbucket workspaces
- **Repository Access**: Browse repositories with pagination support and fetch from all workspaces
- **Codebase Exploration**: Get complete repository structure and file contents
- **File Operations**: Retrieve specific file contents and list all files
- **Export Functionality**: Save codebase structures to JSON files
- **Optimized Architecture**: Internal functions prevent tool-to-tool calls and enable code reuse

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Authentication

Create a `.env` file in the project root with your Bitbucket credentials:

```env
BITBUCKET_TOKEN=your_bitbucket_token_here
BITBUCKET_EMAIL=your_bitbucket_email@example.com
```

**To get your Bitbucket token:**

1. Go to [Bitbucket App Passwords](https://bitbucket.org/account/settings/app-passwords/)
2. Click "Create app password"
3. Give it a name (e.g., "MCP Server")
4. Select permissions: "Account Read", "Repositories Read"
5. Copy the generated token

### 3. MCP Configuration

Add this to your MCP client configuration (e.g., `mcp_config.json`):

```json
{
  "mcpServers": {
    "bitbucket-server": {
      "command": "python",
      "args": ["bitbucket_mcp_server.py"],
      "env": {
        "BITBUCKET_TOKEN": "your_bitbucket_token_here",
        "BITBUCKET_EMAIL": "your_bitbucket_email@example.com"
      }
    }
  }
}
```

## Available Tools

### 1. `authenticate_user`
Authenticate with Bitbucket using your email and token.

**Parameters:**
- `email` (string, optional): Your Bitbucket email address. If not provided, will use the configured BITBUCKET_EMAIL.

**Returns:** User information and authentication status

### 2. `get_workspaces`
Get list of workspaces the user has access to.

**Returns:** List of workspaces with details

### 3. `get_repositories`
Get list of repositories.

**Parameters:**
- `workspace` (optional string): Workspace slug (if not provided, gets repositories from all workspaces)
- `page_size` (int): Number of repositories per page (default: 50)

**Returns:** List of repositories with metadata and workspace details when fetching from all workspaces

### 4. `get_all_repositories_with_workspaces`
Get repositories from all workspaces with detailed workspace information.

**Parameters:**
- `page_size` (int): Number of repositories per page per workspace (default: 50)

**Returns:** Detailed information about repositories organized by workspaces

### 5. `get_repository_branches`
Get list of branches from a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug

**Returns:** List of branches with details, commit information, and default branch identification

### 6. `get_repository_codebase`
Get the complete codebase structure and contents of a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)
- `max_items` (optional int): Maximum number of files/directories to return (for pagination)

**Returns:** Complete repository structure with file contents, or list of available branches if multiple branches exist and no specific branch is specified

### 7. `get_repository_codebase_paginated`
Get a limited number of files/directories from a repository codebase (paginated).

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `max_items` (int): Maximum number of files/directories to return (required for pagination)
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)

**Returns:** Repository structure with limited file contents, or list of available branches if multiple branches exist and no specific branch is specified

### 8. `get_specific_file_content`
Get the content of a specific file from a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `file_path` (string): Path to the file within the repository
- `branch` (string): Branch name (default: 'main')

**Returns:** File content and metadata

### 9. `get_repository_files_list`
Get a list of all files in a repository (without content).

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)

**Returns:** List of all files and code files separately

### 9. `get_pull_requests`
Get pull requests from a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `state` (string): PR state (OPEN, MERGED, DECLINED, SUPERSEDED) - default: OPEN
- `page_size` (int): Number of PRs per page (default: 50)

**Returns:** List of pull requests with details

### 10. `get_pull_request_files`
Get files changed in a pull request.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `pr_id` (int): Pull Request ID

**Returns:** List of files changed in the PR with change details and categorization

### 11. `find_repository`
Search for a repository by name across all accessible workspaces.

**Parameters:**
- `repo_name` (string): Repository name or slug to search for (case-insensitive)
- `page_size` (int): Number of repositories per page per workspace (default: 50)

**Returns:** List of matching repositories with workspace details

### 12. `search_pull_requests`
Search pull requests by title using a descriptive query.

**Parameters:**
- `workspace` (string, optional): Workspace name/slug (optional if repo_name is provided)
- `repo_slug` (string, optional): Repository slug (optional if repo_name is provided)
- `repo_name` (string, optional): Repository name to search for across workspaces (optional if workspace and repo_slug are provided)
- `search_query` (string): Search query to match against PR titles (case-insensitive)
- `state` (string): PR state (OPEN, MERGED, DECLINED, SUPERSEDED) - default: OPEN
- `page_size` (int): Number of PRs per page (default: 50)

**Returns:** List of pull requests matching the search query with their IDs and content

### 13. `get_pull_request_details`
Get comprehensive details about a specific pull request by ID.

**Parameters:**
- `workspace` (string, optional): Workspace name/slug (optional if repo_name is provided)
- `repo_slug` (string, optional): Repository slug (optional if repo_name is provided)
- `repo_name` (string, optional): Repository name to search for across workspaces (optional if workspace and repo_slug are provided)
- `pr_id` (int): Pull Request ID

**Returns:** Comprehensive pull request details including:
- Basic PR information (title, description, state, dates)
- Author and participant information
- Source and destination branch details
- Reviewers and their approval status
- Files changed with change statistics
- Comments and activities
- Links and metadata

### 14. `save_codebase_to_file`
Save the codebase structure to a JSON file.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `filename` (string): Local filename to save to
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)
- `max_items` (optional int): Maximum number of files/directories to save (for pagination)

**Returns:** Success status and file information

## Usage Example

1. **Start the server:**
   ```bash
   python bitbucket_mcp_server.py
   ```

2. **Connect from your MCP client** (e.g., Claude Desktop, Cursor)

3. **Use the tools:**
   - First authenticate (email will be used from config if available)
   - Get your workspaces
   - Browse repositories (now fetches from all workspaces by default)
   - Explore codebases
   - Retrieve specific files



## Architecture Optimizations

The server has been optimized with the following improvements:

### Internal Functions
- **`_authenticate_internal()`**: Internal authentication function used by other functions
- **`_get_workspaces_internal()`**: Internal workspace fetching function
- **`_get_repositories_from_workspace_internal()`**: Internal repository fetching for specific workspaces
- **`_get_user_repositories_internal()`**: Internal user repository fetching
- **`_find_repository_across_workspaces_internal()`**: Internal repository search across all workspaces
- **`_get_repository_branches_internal()`**: Internal branch fetching function
- **`_get_repository_codebase_internal()`**: Internal codebase structure fetching
- **`_get_specific_file_content_internal()`**: Internal file content fetching
- **`_get_repository_files_list_internal()`**: Internal file list fetching
- **`_get_pull_requests_internal()`**: Internal pull request fetching
- **`_search_pull_requests_internal()`**: Internal pull request search by title
- **`_get_pull_request_files_internal()`**: Internal pull request file changes fetching
- **`_get_pull_request_details_internal()`**: Internal comprehensive pull request details fetching

### Benefits
- **No Tool-to-Tool Calls**: Internal functions prevent MCP tools from calling other tools
- **Code Reuse**: Common functionality is shared through internal functions
- **Better Error Handling**: Consistent error handling across all functions
- **Automatic Authentication**: Functions can automatically authenticate if credentials are configured
- **Enhanced Repository Fetching**: `get_repositories()` now fetches from all workspaces when no specific workspace is provided
- **Repository Discovery**: Search for repositories by name across all accessible workspaces
- **Branch Management**: New tools for fetching repository branches and intelligent branch selection
- **Pull Request Management**: Comprehensive tools for fetching PRs, searching by title, and analyzing file changes
- **PR Details**: Get complete pull request information including reviewers, participants, files changed, comments, and activities
- **Codebase Pagination**: Support for limiting the number of files/directories returned to improve performance

## Security Notes

- Store your Bitbucket token and email securely in environment variables
- Never commit tokens to version control
- Use app passwords with minimal required permissions
- The server maintains authentication state during the session
- Email can be configured once and reused across sessions

## Troubleshooting

### Authentication Issues
- Ensure you're using the correct email address
- Verify your token has the required permissions
- Check if your token has expired

### Repository Access Issues
- Make sure you have access to the workspace/repository
- Verify the workspace slug and repository slug are correct
- Check if the repository is private and you have proper access

### File Content Issues
- Some file types may not return content (binary files, large files)
- Check if the file path is correct
- Verify the branch exists

## Dependencies

- `fastmcp`: MCP server framework
- `requests`: HTTP client for API calls
- `pydantic`: Data validation
- `python-dotenv`: Environment variable management

## License

This project is open source and available under the MIT License. 