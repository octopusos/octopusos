/**
 * Snippets API Utilities
 *
 * Provides wrapper functions for all Snippets API endpoints.
 * Coverage: POST /api/snippets, GET /api/snippets, GET /api/snippets/{id},
 *           PATCH /api/snippets/{id}, DELETE /api/snippets/{id}, POST /api/snippets/{id}/explain
 */

/**
 * Create a new snippet
 *
 * @param {Object} data - Snippet data
 * @param {string} data.title - Snippet title
 * @param {string} data.content - Snippet code content
 * @param {string} data.language - Programming language
 * @param {string} [data.description] - Optional description
 * @param {Array<string>} [data.tags] - Optional tags
 * @param {string} [data.source] - Optional source identifier
 * @returns {Promise<Object>} API response with created snippet
 */
async function createSnippet(data) {
    try {
        const response = await apiClient.post('/api/snippets', data, {
            requestId: `snippet-create-${Date.now()}`
        });
        return response;
    } catch (error) {
        console.error('Failed to create snippet:', error);
        throw error;
    }
}

/**
 * List snippets with optional filters
 *
 * @param {Object} options - Query options
 * @param {string} [options.query] - Full-text search query
 * @param {string} [options.tag] - Filter by tag
 * @param {string} [options.language] - Filter by language
 * @param {number} [options.limit=50] - Maximum results
 * @returns {Promise<Object>} API response with snippets array
 */
async function listSnippets(options = {}) {
    try {
        const params = new URLSearchParams();

        if (options.query) {
            params.append('q', options.query);
        }
        if (options.tag) {
            params.append('tag', options.tag);
        }
        if (options.language) {
            params.append('language', options.language);
        }
        if (options.limit) {
            params.append('limit', options.limit);
        }

        const url = `/api/snippets${params.toString() ? '?' + params.toString() : ''}`;
        const response = await apiClient.get(url, {
            requestId: `snippet-list-${Date.now()}`
        });

        return response;
    } catch (error) {
        console.error('Failed to list snippets:', error);
        throw error;
    }
}

/**
 * Get snippet by ID
 *
 * @param {number} id - Snippet ID
 * @returns {Promise<Object>} API response with snippet details
 */
async function getSnippet(id) {
    try {
        const response = await apiClient.get(`/api/snippets/${id}`, {
            requestId: `snippet-get-${id}`
        });
        return response;
    } catch (error) {
        console.error('Failed to get snippet:', error);
        throw error;
    }
}

/**
 * Update snippet
 *
 * @param {number} id - Snippet ID
 * @param {Object} data - Updated snippet data
 * @param {string} [data.title] - Updated title
 * @param {string} [data.content] - Updated content
 * @param {string} [data.description] - Updated description
 * @param {Array<string>} [data.tags] - Updated tags
 * @returns {Promise<Object>} API response with updated snippet
 */
async function updateSnippet(id, data) {
    try {
        const response = await apiClient.patch(`/api/snippets/${id}`, data, {
            requestId: `snippet-update-${id}`
        });
        return response;
    } catch (error) {
        console.error('Failed to update snippet:', error);
        throw error;
    }
}

/**
 * Delete snippet
 *
 * @param {number} id - Snippet ID
 * @returns {Promise<Object>} API response
 */
async function deleteSnippet(id) {
    try {
        const response = await apiClient.delete(`/api/snippets/${id}`, {
            requestId: `snippet-delete-${id}`
        });
        return response;
    } catch (error) {
        console.error('Failed to delete snippet:', error);
        throw error;
    }
}

/**
 * Generate explanation for snippet
 *
 * @param {number} id - Snippet ID
 * @param {Object} options - Options
 * @param {string} [options.lang] - Language for prompt (zh or en)
 * @returns {Promise<Object>} API response with explanation prompt
 */
async function explainSnippet(id, options = {}) {
    try {
        const { lang = 'zh' } = options;
        const response = await apiClient.post(
            `/api/snippets/${id}/explain?lang=${lang}`,
            {},
            { requestId: `snippet-explain-${id}` }
        );
        return response;
    } catch (error) {
        console.error('Failed to explain snippet:', error);
        return { ok: false, message: error.message };
    }
}

/**
 * Get all unique tags from snippets
 *
 * @returns {Promise<Array<string>>} Array of unique tags
 */
async function getSnippetTags() {
    try {
        const response = await listSnippets({ limit: 1000 });
        if (response.ok && response.data && response.data.snippets) {
            const tagsSet = new Set();
            response.data.snippets.forEach(snippet => {
                if (snippet.tags && Array.isArray(snippet.tags)) {
                    snippet.tags.forEach(tag => tagsSet.add(tag));
                }
            });
            return Array.from(tagsSet).sort();
        }
        return [];
    } catch (error) {
        console.error('Failed to get snippet tags:', error);
        return [];
    }
}

/**
 * Get all unique languages from snippets
 *
 * @returns {Promise<Array<string>>} Array of unique languages
 */
async function getSnippetLanguages() {
    try {
        const response = await listSnippets({ limit: 1000 });
        if (response.ok && response.data && response.data.snippets) {
            const languagesSet = new Set();
            response.data.snippets.forEach(snippet => {
                if (snippet.language) {
                    languagesSet.add(snippet.language);
                }
            });
            return Array.from(languagesSet).sort();
        }
        return [];
    } catch (error) {
        console.error('Failed to get snippet languages:', error);
        return [];
    }
}

/**
 * Create preview from snippet
 *
 * @param {string} snippetId - Snippet ID
 * @param {string} preset - Preview preset (default: 'html-basic')
 * @returns {Promise<Object>} Preview session data
 */
async function previewSnippet(snippetId, preset = 'html-basic') {
    try {
        const response = await apiClient.post(`/api/snippets/${snippetId}/preview`, {
            preset: preset
        }, {
            requestId: `snippet-preview-${snippetId}`
        });
        return response;
    } catch (error) {
        console.error('Failed to create preview:', error);
        throw error;
    }
}

/**
 * Materialize snippet to task draft
 *
 * @param {string} snippetId - Snippet ID
 * @param {string} targetPath - Target file path (relative)
 * @param {string} description - Optional task description
 * @returns {Promise<Object>} Task draft data
 */
async function materializeSnippet(snippetId, targetPath, description = null) {
    try {
        const response = await apiClient.post(`/api/snippets/${snippetId}/materialize`, {
            target_path: targetPath,
            description: description
        }, {
            requestId: `snippet-materialize-${snippetId}`
        });
        return response;
    } catch (error) {
        console.error('Failed to materialize snippet:', error);
        throw error;
    }
}

// Export to global scope
window.SnippetsAPI = {
    createSnippet,
    listSnippets,
    getSnippet,
    updateSnippet,
    deleteSnippet,
    explainSnippet,
    getSnippetTags,
    getSnippetLanguages,
    previewSnippet,
    materializeSnippet
};
