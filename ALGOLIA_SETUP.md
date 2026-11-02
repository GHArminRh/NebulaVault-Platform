# Algolia Search — Nebula Vault

Set these environment variables on Render and in local development:

- \`ALGOLIA_APP_ID\`: Application ID from Algolia.
- \`ALGOLIA_ADMIN_API_KEY\`: private Admin API key. Never expose or commit it.
- \`ALGOLIA_SEARCH_API_KEY\`: restricted Search-only key; this is public in the browser.
- \`ALGOLIA_PRODUCTS_INDEX\`: optional, defaults to \`nebula_products\`.
- \`ALGOLIA_ARTICLES_INDEX\`: optional, defaults to \`nebula_articles\`.

Create a restricted Search API key with only the \`search\` ACL and restrict it to those two index names. Never put the Admin API key in frontend code.

After deploying with the environment variables, run:

\`\`\`bash
python manage.py reindex_algolia
\`\`\`

The command applies search settings, clears only the two configured public indexes, and rebuilds them from active products and published articles. Do not configure these index names to point at unrelated data.

Product, release, article, and article-tag changes are synchronized after database commits. Draft/unpublished articles and inactive products are removed from the public indexes.

The current Free plan includes 10,000 search requests/month and 50,000 records. Product and article searches are combined into one multi-index request, with a 260ms debounce and a two-character minimum. Search-as-you-type still consumes requests.
