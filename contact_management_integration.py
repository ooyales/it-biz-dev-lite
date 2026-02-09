"""
Contact Management System Integration
Add this to team_dashboard_app.py

Instructions:
1. Open team_dashboard_app.py
2. Find the line: if __name__ == '__main__':
3. Paste this entire file BEFORE that line
4. Save and restart the dashboard
"""

# ============================================================================
# CONTACT MANAGEMENT ROUTES
# ============================================================================

@app.route('/contacts/manage')
def contacts_management():
    """Serve full-featured contact management interface"""
    return render_template('contacts-management.html')


# ============================================================================
# CONTACT MANAGEMENT API ENDPOINTS
# ============================================================================

@app.route('/api/contacts', methods=['POST'])
def create_contact():
    """Create new contact"""
    try:
        data = request.json
        
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO contacts (
                first_name, last_name, title, organization, department,
                email, phone, linkedin_url, agency, office_symbol, location,
                clearance_level, role_type, influence_level, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('first_name'),
            data.get('last_name'),
            data.get('title'),
            data.get('organization'),
            data.get('department'),
            data.get('email'),
            data.get('phone'),
            data.get('linkedin_url'),
            data.get('agency'),
            data.get('office_symbol'),
            data.get('location'),
            data.get('clearance_level'),
            data.get('role_type'),
            data.get('influence_level'),
            data.get('notes')
        ))
        
        contact_id = c.lastrowid
        
        # Add tags
        if data.get('tags'):
            for tag in data['tags']:
                if tag.strip():
                    c.execute("""
                        INSERT INTO contact_tags (contact_id, tag)
                        VALUES (?, ?)
                    """, (contact_id, tag.strip()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': contact_id})
        
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """Update existing contact"""
    try:
        data = request.json
        
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("""
            UPDATE contacts SET
                first_name = ?, last_name = ?, title = ?, organization = ?,
                department = ?, email = ?, phone = ?, linkedin_url = ?,
                agency = ?, office_symbol = ?, location = ?, clearance_level = ?,
                role_type = ?, influence_level = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get('first_name'),
            data.get('last_name'),
            data.get('title'),
            data.get('organization'),
            data.get('department'),
            data.get('email'),
            data.get('phone'),
            data.get('linkedin_url'),
            data.get('agency'),
            data.get('office_symbol'),
            data.get('location'),
            data.get('clearance_level'),
            data.get('role_type'),
            data.get('influence_level'),
            data.get('notes'),
            contact_id
        ))
        
        # Update tags - delete old and insert new
        c.execute("DELETE FROM contact_tags WHERE contact_id = ?", (contact_id,))
        
        if data.get('tags'):
            for tag in data['tags']:
                if tag.strip():
                    c.execute("""
                        INSERT INTO contact_tags (contact_id, tag)
                        VALUES (?, ?)
                    """, (contact_id, tag.strip()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Delete contact"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Delete related records first
        c.execute("DELETE FROM contact_tags WHERE contact_id = ?", (contact_id,))
        c.execute("DELETE FROM interactions WHERE contact_id = ?", (contact_id,))
        c.execute("DELETE FROM contact_relationships WHERE contact_id_1 = ? OR contact_id_2 = ?", 
                 (contact_id, contact_id))
        c.execute("DELETE FROM opportunity_contacts WHERE contact_id = ?", (contact_id,))
        
        # Delete contact
        c.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/contacts/import/preview', methods=['POST'])
def preview_import():
    """Preview contacts from uploaded file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        filename = file.filename
        
        # Read file based on extension
        if filename.endswith('.csv'):
            import pandas as pd
            df = pd.read_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            import pandas as pd
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        # Preview first 5 rows
        preview = df.head(5).to_dict('records')
        
        return jsonify({
            'preview': preview,
            'total': len(df),
            'columns': list(df.columns)
        })
        
    except Exception as e:
        logger.error(f"Error previewing import: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/contacts/import', methods=['POST'])
def import_contacts():
    """Import contacts from file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        filename = file.filename
        
        # Read file
        import pandas as pd
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        # Normalize column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
        
        conn = db.get_connection()
        c = conn.cursor()
        
        imported = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Check required fields
                if pd.isna(row.get('first_name')) or pd.isna(row.get('last_name')) or pd.isna(row.get('agency')):
                    errors.append(f"Row {idx+2}: Missing required fields")
                    continue
                
                # Insert contact
                c.execute("""
                    INSERT INTO contacts (
                        first_name, last_name, title, organization, department,
                        email, phone, linkedin_url, agency, office_symbol, location,
                        clearance_level, role_type, influence_level, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('first_name', '')),
                    str(row.get('last_name', '')),
                    str(row.get('title', '')) if pd.notna(row.get('title')) else None,
                    str(row.get('organization', '')) if pd.notna(row.get('organization')) else None,
                    str(row.get('department', '')) if pd.notna(row.get('department')) else None,
                    str(row.get('email', '')) if pd.notna(row.get('email')) else None,
                    str(row.get('phone', '')) if pd.notna(row.get('phone')) else None,
                    str(row.get('linkedin_url', '')) if pd.notna(row.get('linkedin_url')) else None,
                    str(row.get('agency', '')),
                    str(row.get('office_symbol', '')) if pd.notna(row.get('office_symbol')) else None,
                    str(row.get('location', '')) if pd.notna(row.get('location')) else None,
                    str(row.get('clearance_level', '')) if pd.notna(row.get('clearance_level')) else None,
                    str(row.get('role_type', '')) if pd.notna(row.get('role_type')) else None,
                    str(row.get('influence_level', '')) if pd.notna(row.get('influence_level')) else None,
                    str(row.get('notes', '')) if pd.notna(row.get('notes')) else None
                ))
                
                contact_id = c.lastrowid
                
                # Add tags
                tags_str = row.get('tags', '')
                if pd.notna(tags_str) and tags_str:
                    tags = [t.strip() for t in str(tags_str).split(',')]
                    for tag in tags:
                        if tag:
                            c.execute("""
                                INSERT INTO contact_tags (contact_id, tag)
                                VALUES (?, ?)
                            """, (contact_id, tag))
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {idx+2}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error importing contacts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/contacts/duplicates')
def find_duplicates():
    """Find potential duplicate contacts"""
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Find duplicates by name
        c.execute("""
            SELECT first_name, last_name, COUNT(*) as count
            FROM contacts
            GROUP BY first_name, last_name
            HAVING count > 1
        """)
        
        name_duplicates = c.fetchall()
        
        duplicates = []
        
        # Get contacts for each duplicate group
        for first_name, last_name, count in name_duplicates:
            c.execute("""
                SELECT id, first_name, last_name, title, organization, email, phone
                FROM contacts
                WHERE first_name = ? AND last_name = ?
            """, (first_name, last_name))
            
            contacts = []
            for row in c.fetchall():
                contacts.append({
                    'id': row[0],
                    'first_name': row[1],
                    'last_name': row[2],
                    'title': row[3],
                    'organization': row[4],
                    'email': row[5],
                    'phone': row[6]
                })
            
            duplicates.append({
                'type': 'name',
                'contacts': contacts
            })
        
        conn.close()
        
        return jsonify(duplicates)
        
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        return jsonify({'error': str(e)}), 500


# End of Contact Management Integration
