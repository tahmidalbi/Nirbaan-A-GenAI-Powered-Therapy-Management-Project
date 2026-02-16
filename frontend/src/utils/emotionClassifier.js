/**
 * Classify emotion from transcript text using OpenAI
 * @param {string} text - The transcript text to analyze
 * @returns {Promise<string>} - One of: happy, sad, anxious, angry, neutral
 */
export const classifyEmotion = async (text) => {
  try {
    const apiKey = import.meta.env.VITE_OPENAI_API_KEY;
    
    if (!apiKey) {
      console.warn('OpenAI API key not found, defaulting to neutral');
      return 'neutral';
    }

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are an emotion classifier. Analyze the given text and respond with ONLY ONE word from this list: happy, sad, anxious, angry, neutral. Do not include any other text, punctuation, or explanation.',
          },
          {
            role: 'user',
            content: `Classify the emotion in this text: "${text}"`,
          },
        ],
        temperature: 0.3,
        max_tokens: 10,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.status}`);
    }

    const data = await response.json();
    const emotion = data.choices[0].message.content.trim().toLowerCase();

    // Validate emotion is one of the allowed values
    const validEmotions = ['happy', 'sad', 'anxious', 'angry', 'neutral'];
    if (validEmotions.includes(emotion)) {
      return emotion;
    }

    // Default to neutral if invalid response
    return 'neutral';
  } catch (error) {
    console.error('Error classifying emotion:', error);
    return 'neutral';
  }
};
