/**
 * DataTable - Generic data table component
 *
 * Features:
 * - Column rendering
 * - Empty state
 * - Loading state
 * - Row click handler
 * - Pagination support
 *
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class DataTable {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.options = {
            columns: options.columns || [],
            data: options.data || [],
            emptyText: options.emptyText || 'No data available',
            loadingText: options.loadingText || 'Loading...',
            onRowClick: options.onRowClick || null,
            rowClassName: options.rowClassName || null,
            pagination: options.pagination || false,
            pageSize: options.pageSize || 20,
            ...options,
        };

        this.state = {
            loading: false,
            currentPage: 0,
        };

        this.render();
    }

    /**
     * Render the table
     */
    render() {
        this.container.innerHTML = '';
        this.container.className = 'data-table-container';

        // Loading state
        if (this.state.loading) {
            this.renderLoading();
            return;
        }

        // Empty state
        if (this.options.data.length === 0) {
            this.renderEmpty();
            return;
        }

        // Table
        const table = document.createElement('table');
        table.className = 'data-table';

        // Header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        this.options.columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = column.label || column.key;
            if (column.width) {
                th.style.width = column.width;
            }
            if (column.align) {
                th.style.textAlign = column.align;
            }
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Body
        const tbody = document.createElement('tbody');

        const pageData = this.options.pagination
            ? this.getPageData()
            : this.options.data;

        pageData.forEach((row, index) => {
            const tr = document.createElement('tr');

            // Row class name
            if (this.options.rowClassName) {
                const className = typeof this.options.rowClassName === 'function'
                    ? this.options.rowClassName(row, index)
                    : this.options.rowClassName;
                if (className) {
                    tr.className = className;
                }
            }

            // Row click handler
            if (this.options.onRowClick) {
                tr.style.cursor = 'pointer';
                tr.onclick = (e) => this.options.onRowClick(row, e);
            }

            // Cells
            this.options.columns.forEach(column => {
                const td = document.createElement('td');

                if (column.align) {
                    td.style.textAlign = column.align;
                }

                // Render cell content
                if (column.render) {
                    const content = column.render(row[column.key], row, index);
                    if (typeof content === 'string') {
                        td.innerHTML = content;
                    } else if (content && content.nodeType) {
                        // Check if it's a valid DOM node
                        td.appendChild(content);
                    } else {
                        // Fallback for invalid content
                        td.textContent = content !== null && content !== undefined ? String(content) : '-';
                    }
                } else {
                    const value = this.getCellValue(row, column.key);
                    td.textContent = value !== null && value !== undefined ? value : '-';
                }

                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        this.container.appendChild(table);

        // Pagination
        if (this.options.pagination) {
            this.renderPagination();
        }
    }

    /**
     * Get cell value (supports nested keys like "user.name")
     */
    getCellValue(row, key) {
        if (!key.includes('.')) {
            return row[key];
        }

        const keys = key.split('.');
        let value = row;

        for (const k of keys) {
            if (value === null || value === undefined) {
                return null;
            }
            value = value[k];
        }

        return value;
    }

    /**
     * Render loading state
     */
    renderLoading() {
        const loading = document.createElement('div');
        loading.className = 'data-table-state loading';
        loading.innerHTML = `
            <div class="spinner"></div>
            <p>${this.options.loadingText}</p>
        `;
        this.container.appendChild(loading);
    }

    /**
     * Render empty state
     */
    renderEmpty() {
        const empty = document.createElement('div');
        empty.className = 'data-table-state empty';
        empty.innerHTML = `
            <div class="empty-icon"><span class="material-icons md-36">inbox</span></div>
            <p>${this.options.emptyText}</p>
        `;
        this.container.appendChild(empty);
    }

    /**
     * Get page data
     */
    getPageData() {
        const start = this.state.currentPage * this.options.pageSize;
        const end = start + this.options.pageSize;
        return this.options.data.slice(start, end);
    }

    /**
     * Render pagination
     */
    renderPagination() {
        const totalPages = Math.ceil(this.options.data.length / this.options.pageSize);

        if (totalPages <= 1) {
            return;
        }

        const pagination = document.createElement('div');
        pagination.className = 'data-table-pagination';

        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '‹ Previous';
        prevBtn.className = 'pagination-btn';
        prevBtn.disabled = this.state.currentPage === 0;
        prevBtn.onclick = () => this.goToPage(this.state.currentPage - 1);
        pagination.appendChild(prevBtn);

        // Page info
        const pageInfo = document.createElement('span');
        pageInfo.className = 'pagination-info';
        pageInfo.textContent = `Page ${this.state.currentPage + 1} of ${totalPages}`;
        pagination.appendChild(pageInfo);

        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next ›';
        nextBtn.className = 'pagination-btn';
        nextBtn.disabled = this.state.currentPage >= totalPages - 1;
        nextBtn.onclick = () => this.goToPage(this.state.currentPage + 1);
        pagination.appendChild(nextBtn);

        this.container.appendChild(pagination);
    }

    /**
     * Go to page
     */
    goToPage(page) {
        const totalPages = Math.ceil(this.options.data.length / this.options.pageSize);

        if (page < 0 || page >= totalPages) {
            return;
        }

        this.state.currentPage = page;
        this.render();
    }

    /**
     * Update data
     */
    setData(data) {
        this.options.data = data;
        this.state.currentPage = 0;
        this.render();
    }

    /**
     * Set loading state
     */
    setLoading(loading) {
        this.state.loading = loading;
        this.render();
    }

    /**
     * Update columns
     */
    setColumns(columns) {
        this.options.columns = columns;
        this.render();
    }

    /**
     * Refresh (re-render)
     */
    refresh() {
        this.render();
    }

    /**
     * Destroy component (cleanup)
     */
    destroy() {
        // Clear data
        this.data = [];
        // Clear container
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export to window
window.DataTable = DataTable;
