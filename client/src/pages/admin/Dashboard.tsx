import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
} from '@mui/material';

interface LaundryRequest {
  id: number;
  student_id: string;
  student_name: string;
  num_clothes: number;
  status: string;
  submission_date: string;
}

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [requests, setRequests] = React.useState<LaundryRequest[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] = React.useState<number | null>(null);
  const [newStatus, setNewStatus] = React.useState<string>('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    const fetchRequests = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/admin/dashboard', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            localStorage.removeItem('token');
            navigate('/login');
            return;
          }
          throw new Error('Failed to fetch requests');
        }

        const data = await response.json();
        setRequests(data.requests);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, [navigate]);

  const handleUpdateStatus = async (requestId: number, newStatus: string) => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    try {
      const response = await fetch(`http://localhost:3001/api/admin/requests/${requestId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) {
        throw new Error('Failed to update status');
      }

      // Refresh the requests list
      const updatedRequests = requests.map(request =>
        request.id === requestId ? { ...request, status: newStatus } : request
      );
      setRequests(updatedRequests);
      setSelectedRequest(null);
      setNewStatus('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleStatusChange = (event: SelectChangeEvent<string>) => {
    setNewStatus(event.target.value);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Admin Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 440 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Student ID</TableCell>
                <TableCell>Student Name</TableCell>
                <TableCell>Number of Clothes</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Submission Date</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {requests.map((request) => (
                <TableRow key={request.id}>
                  <TableCell>{request.student_id}</TableCell>
                  <TableCell>{request.student_name}</TableCell>
                  <TableCell>{request.num_clothes}</TableCell>
                  <TableCell>{request.status}</TableCell>
                  <TableCell>
                    {new Date(request.submission_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {request.status !== 'completed' && (
                      <Button
                        variant="contained"
                        color="primary"
                        size="small"
                        onClick={() => setSelectedRequest(request.id)}
                      >
                        Update Status
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Dialog open={!!selectedRequest} onClose={() => setSelectedRequest(null)}>
        <DialogTitle>Update Request Status</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>New Status</InputLabel>
            <Select
              value={newStatus}
              label="New Status"
              onChange={handleStatusChange}
            >
              <MenuItem value="processing">Processing</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedRequest(null)}>Cancel</Button>
          <Button
            onClick={() => selectedRequest && handleUpdateStatus(selectedRequest, newStatus)}
            variant="contained"
            disabled={!newStatus}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AdminDashboard;