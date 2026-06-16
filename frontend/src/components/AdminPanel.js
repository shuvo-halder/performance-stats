import React, { useState, useEffect, useCallback } from 'react';
import { listUsers, approveUser, rejectUser, makeAdmin } from '../api';

function AdminPanel({ onClose }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const fetchUsers = useCallback(async () => {
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleApprove = async (userId) => {
    try {
      const res = await approveUser(userId);
      setMessage(res.message);
      fetchUsers();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const handleReject = async (userId) => {
    try {
      const res = await rejectUser(userId);
      setMessage(res.message);
      fetchUsers();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const handleMakeAdmin = async (userId) => {
    try {
      const res = await makeAdmin(userId);
      setMessage(res.message);
      fetchUsers();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const pendingUsers = users.filter(u => !u.is_approved);
  const approvedUsers = users.filter(u => u.is_approved);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>👥 User Management</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {message && <div className="modal-message">{message}</div>}

        {loading ? (
          <div className="loading-screen" style={{ minHeight: 200 }}>
            <div className="spinner"></div>
          </div>
        ) : (
          <div className="modal-body">
            {pendingUsers.length > 0 && (
              <>
                <h3 className="user-section-title">⏳ Pending Approval ({pendingUsers.length})</h3>
                <div className="users-table">
                  <div className="users-header">
                    <span>Username</span>
                    <span>Email</span>
                    <span>Registered</span>
                    <span>Actions</span>
                  </div>
                  {pendingUsers.map(u => (
                    <div key={u.id} className="users-row pending">
                      <span className="user-name">{u.username}</span>
                      <span className="user-email">{u.email}</span>
                      <span className="user-date">{new Date(u.created_at).toLocaleDateString()}</span>
                      <span className="user-actions">
                        <button className="action-btn approve" onClick={() => handleApprove(u.id)}>✅ Approve</button>
                        <button className="action-btn reject" onClick={() => handleReject(u.id)}>❌ Reject</button>
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <h3 className="user-section-title">✅ Approved Users ({approvedUsers.length})</h3>
            <div className="users-table">
              <div className="users-header">
                <span>Username</span>
                <span>Email</span>
                <span>Role</span>
                <span>Actions</span>
              </div>
              {approvedUsers.map(u => (
                <div key={u.id} className="users-row approved">
                  <span className="user-name">{u.username}</span>
                  <span className="user-email">{u.email}</span>
                  <span className="user-role">
                    {u.is_admin ? <span className="admin-badge">Admin</span> : <span className="user-badge">User</span>}
                  </span>
                  <span className="user-actions">
                    {!u.is_admin && (
                      <button className="action-btn promote" onClick={() => handleMakeAdmin(u.id)}>👑 Make Admin</button>
                    )}
                    <button className="action-btn reject" onClick={() => handleReject(u.id)}>🚫 Disable</button>
                  </span>
                </div>
              ))}
            </div>

            {users.length === 0 && <p className="no-data">No users found</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminPanel;