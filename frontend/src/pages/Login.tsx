import React, { useState } from 'react';
import {
  Box,
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Tab,
  Tabs,
  Alert,
} from '@mui/material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

interface LoginFormValues {
  username: string;
  password: string;
}

const validationSchema = yup.object({
  username: yup.string().required('Username is required'),
  password: yup.string().required('Password is required'),
});

const Login = () => {
  const navigate = useNavigate();
  const [userType, setUserType] = useState<'student' | 'admin'>('student');
  const [error, setError] = useState<string | null>(null);

  const formik = useFormik<LoginFormValues>({
    initialValues: {
      username: '',
      password: '',
    },
    validationSchema: validationSchema,
    onSubmit: async (values) => {
      try {
        const response = await client.post('/auth/login', {
          username: values.username,
          password: values.password,
          role: userType,
        });

        const { token, user } = response.data;

        // Store the token and user info
        localStorage.setItem('token', token);
        localStorage.setItem('userType', userType);

        // Redirect based on user type
        navigate(userType === 'student' ? '/student/dashboard' : '/admin/dashboard');
      } catch (err: any) {
        setError(err.response?.data?.message || err.message || 'An error occurred during login');
      }
    },
  });

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          Alpha Laundry
        </Typography>
        <Typography variant="h5" component="h2" gutterBottom align="center">
          Login to Your Account
        </Typography>
      </Box>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Tabs
          value={userType}
          onChange={(_, newValue) => setUserType(newValue)}
          centered
          sx={{ mb: 3 }}
        >
          <Tab label="Student" value="student" />
          <Tab label="Admin" value="admin" />
        </Tabs>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={formik.handleSubmit}>
          <TextField
            fullWidth
            id="username"
            name="username"
            label={userType === 'student' ? 'Student ID' : 'Username'}
            value={formik.values.username}
            onChange={formik.handleChange}
            error={formik.touched.username && Boolean(formik.errors.username)}
            helperText={formik.touched.username && formik.errors.username}
            margin="normal"
          />
          <TextField
            fullWidth
            id="password"
            name="password"
            label="Password"
            type="password"
            value={formik.values.password}
            onChange={formik.handleChange}
            error={formik.touched.password && Boolean(formik.errors.password)}
            helperText={formik.touched.password && formik.errors.password}
            margin="normal"
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            size="large"
            sx={{ mt: 3 }}
          >
            Login
          </Button>
        </form>
      </Paper>
    </Container>
  );
};

export default Login; 