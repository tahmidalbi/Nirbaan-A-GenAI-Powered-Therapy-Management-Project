import NirbaanAITherapistChat from '../components/NirbaanAITherapistChat';
import { useNavigate } from 'react-router-dom';
import './TherapistNirbaanAIPage.css';

export default function TherapistNirbaanAIPage() {
  const navigate = useNavigate();

  return (
    <div className="tnai-page">
      <NirbaanAITherapistChat onBack={() => navigate('/therapist/dashboard')} />
    </div>
  );
}
