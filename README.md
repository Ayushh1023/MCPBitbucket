# Bitbucket MCP Server

A Model Context Protocol (MCP) server built with FastMCP that provides access to Bitbucket repositories and codebases.

## Features

- **Authentication**: Secure authentication with Bitbucket using email and personal access token
- **Workspace Management**: List and access Bitbucket workspaces
- **Repository Access**: Browse repositories with pagination support
- **Codebase Exploration**: Get complete repository structure and file contents
- **File Operations**: Retrieve specific file contents and list all files
- **Export Functionality**: Save codebase structures to JSON files

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
- `workspace` (optional string): Workspace slug (if not provided, gets user's repositories)
- `page_size` (int): Number of repositories per page (default: 50)

**Returns:** List of repositories with metadata

### 4. `get_repository_codebase`
Get the complete codebase structure and contents of a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)

**Returns:** Complete repository structure with file contents

### 5. `get_specific_file_content`
Get the content of a specific file from a repository.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `file_path` (string): Path to the file within the repository
- `branch` (string): Branch name (default: 'main')

**Returns:** File content and metadata

### 6. `get_repository_files_list`
Get a list of all files in a repository (without content).

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)

**Returns:** List of all files and code files separately

### 7. `save_codebase_to_file`
Save the codebase structure to a JSON file.

**Parameters:**
- `workspace` (string): Workspace name/slug
- `repo_slug` (string): Repository slug
- `filename` (string): Local filename to save to
- `branch` (string): Branch name (default: 'main')
- `path` (string): Path within the repository (default: root)

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
   - Browse repositories
   - Explore codebases
   - Retrieve specific files

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