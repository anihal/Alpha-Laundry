import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import client from '../../api/client';
import { format } from 'date-fns';

interface DashboardData {
  student: {
    student_id: string;
    name: string;
    remaining_quota: number;
  };
  recent_requests: Array<{
    id: number;
    num_clothes: number;
    status: string;
    submission_date: string;
  }>;
}

const validationSchema = yup.object({
  num_clothes: yup
    .number()
    .required('Number of clothes is required')
    .min(1, 'Must be at least 1')
    .max(30, 'Cannot exceed 30'),
});

const Dashboard: React.FC = () => {
  const [open, setOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await client.get('/student/dashboard');
      return response.data.data;
    },
  });

  const formik = useFormik({
    initialValues: {
      num_clothes: '',
    },
    validationSchema: validationSchema,
    onSubmit: async (values) => {
      try {
        await client.post('/student/submit', {
          num_clothes: parseInt(values.num_clothes),
        });
        setOpen(false);
        refetch();
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to submit request');
      }
    },
  });

  if (isLoading) {
    return <LinearProgress />;
  }

  if (!data) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
        return 'primary';
      case 'processing':
        return 'warning';
      case 'completed':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Welcome, {data.student.name}
        </Typography>
        <Button
          variant="contained"
          onClick={() => setOpen(true)}
          disabled={data.student.remaining_quota <= 0}
        >
          Submit New Request
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Remaining Quota
              </Typography>
              <Typography variant="h3" color="primary">
                {data.student.remaining_quota}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                out of 30 clothes
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(data.student.remaining_quota / 30) * 100}
                sx={{ mt: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Requests
              </Typography>
              <List>
                {data.recent_requests.map((request) => (
                  <ListItem key={request.id} divider>
                    <ListItemText
                      primary={`${request.num_clothes} clothes`}
                      secondary={format(new Date(request.submission_date), 'PPP')}
                    />
                    <Chip
                      label={request.status}
                      color={getStatusColor(request.status)}
                      size="small"
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Submit New Request</DialogTitle>
        <DialogContent>
          <form onSubmit={formik.handleSubmit}>
            <TextField
              fullWidth
              id="num_clothes"
              name="num_clothes"
              label="Number of Clothes"
              type="number"
              value={formik.values.num_clothes}
              onChange={formik.handleChange}
              error={formik.touched.num_clothes && Boolean(formik.errors.num_clothes)}
              helperText={formik.touched.num_clothes && formik.errors.num_clothes}
              sx={{ mt: 2 }}
            />
            {error && (
              <Typography color="error" sx={{ mt: 1 }}>
                {error}
              </Typography>
            )}
          </form>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={() => formik.handleSubmit()}
            variant="contained"
            disabled={formik.isSubmitting}
          >
            Submit
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Dashboard; 