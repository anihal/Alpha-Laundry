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
import client from '../../api/client';

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
    const fetchRequests = async () => {
      try {
        const response = await client.get('/admin/dashboard');
        setRequests(response.data.data.pending_requests);
      } catch (err: any) {
        setError(err.response?.data?.message || err.message || 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, [navigate]);

  const handleUpdateStatus = async (requestId: number, newStatus: string) => {
    try {
      await client.patch(`/admin/update-status`, {
        request_id: requestId,
        status: newStatus,
      });

      // Refresh the requests list
      const updatedRequests = requests.map(request =>
        request.id === requestId ? { ...request, status: newStatus } : request
      );
      setRequests(updatedRequests);
      setSelectedRequest(null);
      setNewStatus('');
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to update status');
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