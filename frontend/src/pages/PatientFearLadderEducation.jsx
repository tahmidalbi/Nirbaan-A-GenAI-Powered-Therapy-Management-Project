import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import './PatientFearLadderEducation.css';

const PatientFearLadderEducation = () => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleBack = () => {
    navigate('/patient/dashboard/fear-ladder');
  };

  return (
    <div className="fear-ladder-education-container">
      {/* Vintage background */}
      <div className="dashboard-background">
        <div className="geometric-pattern"></div>
        <div className="art-deco-line art-deco-line-top"></div>
        <div className="art-deco-line art-deco-line-bottom"></div>
      </div>

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">Fear Ladder Education</h1>
          <div className="header-actions">
            <button onClick={handleBack} className="back-btn">← Back</button>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="education-main">
        <div className="education-content">
          <h2>Understanding Fear Ladders</h2>
          
          <div className="education-block">
            <h3>What is a Fear Ladder?</h3>
            <p>
              A fear ladder (also called an exposure hierarchy) is a tool used in Exposure and 
              Response Prevention (ERP) therapy for OCD. It helps you organize your fears and 
              obsessions from least to most distressing, creating a structured path for facing 
              your fears gradually.
            </p>
          </div>

          <div className="education-block">
            <h3>What is SUDS?</h3>
            <p>
              SUDS stands for <strong>Subjective Units of Distress Scale</strong>. It's a scale 
              from 0-100 that helps you rate how much anxiety or distress a particular fear causes you:
            </p>
            <ul>
              <li><strong>0-25:</strong> Low anxiety - Mild discomfort</li>
              <li><strong>26-50:</strong> Moderate anxiety - Noticeable distress</li>
              <li><strong>51-75:</strong> High anxiety - Significant distress</li>
              <li><strong>76-100:</strong> Extreme anxiety - Overwhelming distress</li>
            </ul>
          </div>

          <div className="education-block">
            <h3>How to Build Your Fear Ladder</h3>
            <ol>
              <li><strong>Identify your fears:</strong> List all the situations, thoughts, or objects that trigger your OCD</li>
              <li><strong>Rate each fear:</strong> Assign a SUDS rating (0-100) to each item based on your distress level</li>
              <li><strong>Order them:</strong> Arrange items from lowest to highest SUDS rating</li>
              <li><strong>Start small:</strong> Begin ERP with lower-rated items and gradually work your way up</li>
            </ol>
          </div>

          <div className="education-block">
            <h3>Tips for Creating Your Fear Ladder</h3>
            <ul>
              <li>Be specific - Instead of "germs," try "touching a doorknob in a public place"</li>
              <li>Include a range of items - Have items at different difficulty levels</li>
              <li>Be honest - Your SUDS ratings should reflect your true feelings</li>
              <li>Update as needed - Your ratings may change over time as you make progress</li>
            </ul>
          </div>

          <div className="education-example">
            <h3>Example Fear Ladder</h3>
            <table className="example-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>SUDS</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Touching my laptop without washing hands</td>
                  <td>20</td>
                </tr>
                <tr>
                  <td>Touching doorknob at home</td>
                  <td>35</td>
                </tr>
                <tr>
                  <td>Shaking someone's hand</td>
                  <td>50</td>
                </tr>
                <tr>
                  <td>Touching a public doorknob</td>
                  <td>65</td>
                </tr>
                <tr>
                  <td>Using a public restroom</td>
                  <td>80</td>
                </tr>
                <tr>
                  <td>Touching trash can without washing hands after</td>
                  <td>95</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PatientFearLadderEducation;
