import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './FearLadderBuilder.css';

const FearLadderBuilder = ({ onSubmit, existingItems = [], readOnly = false, submitButtonText = "Submit to Therapist" }) => {
  const [ladderItems, setLadderItems] = useState([
    { id: 1, item: '', suds: '' }
  ]);
  const [isReordering, setIsReordering] = useState(false);

  // Load existing items if provided
  useEffect(() => {
    if (existingItems && existingItems.length > 0) {
      const formattedItems = existingItems.map((item, idx) => ({
        id: item.id || idx + 1,
        item: item.item,
        suds: item.suds
      }));
      setLadderItems(formattedItems);
    }
  }, [existingItems]);

  const addNewRow = () => {
    const newId = Math.max(...ladderItems.map(item => item.id), 0) + 1;
    setLadderItems([...ladderItems, { id: newId, item: '', suds: '' }]);
  };

  const updateItem = (id, field, value) => {
    setLadderItems(ladderItems.map(item => 
      item.id === id ? { ...item, [field]: value } : item
    ));
  };

  const deleteRow = (id) => {
    if (ladderItems.length > 1) {
      setLadderItems(ladderItems.filter(item => item.id !== id));
    }
  };

  const reorderBySUDS = () => {
    const sorted = [...ladderItems].sort((a, b) => {
      const sudsA = parseInt(a.suds) || 0;
      const sudsB = parseInt(b.suds) || 0;
      return sudsA - sudsB;
    });
    setLadderItems(sorted);
    setIsReordering(false);
  };

  const handleSubmit = () => {
    // Validate that all items have both item and SUDS values
    const isValid = ladderItems.every(item => 
      item.item.trim() !== '' && item.suds !== '' && !isNaN(item.suds)
    );

    if (!isValid) {
      alert('Please fill in all items and SUDS values with valid numbers');
      return;
    }

    // Sort by SUDS before submitting
    const sortedItems = [...ladderItems].sort((a, b) => 
      parseInt(a.suds) - parseInt(b.suds)
    );

    onSubmit(sortedItems);
  };

  return (
    <div className="fear-ladder-builder">
      <div className="builder-header">
        <h3>{readOnly ? 'Fear Ladder' : 'Build Your Fear Ladder'}</h3>
        <p className="builder-instructions">
          {readOnly 
            ? 'Review the fear ladder items sorted by SUDS rating (0-100).'
            : 'Add your fears or obsessions along with their SUDS rating (0-100). Higher numbers indicate more distress.'
          }
        </p>
      </div>

      <div className="ladder-table">
        <div className="table-header">
          <div className="column-header item-column">ITEM</div>
          <div className="column-header suds-column">SUDS (0-100)</div>
          {!readOnly && <div className="column-header action-column">ACTIONS</div>}
        </div>

        <div className="table-body">
          {ladderItems.map((ladderItem) => (
            <div key={ladderItem.id} className="table-row">
              <div className="table-cell item-column">
                <input
                  type="text"
                  value={ladderItem.item}
                  onChange={(e) => updateItem(ladderItem.id, 'item', e.target.value)}
                  placeholder="Enter your fear or obsession"
                  className="item-input"
                  disabled={readOnly}
                />
              </div>
              <div className="table-cell suds-column">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={ladderItem.suds}
                  onChange={(e) => updateItem(ladderItem.id, 'suds', e.target.value)}
                  placeholder="0-100"
                  className="suds-input"
                  disabled={readOnly}
                />
              </div>
              {!readOnly && (
                <div className="table-cell action-column">
                  <button
                    onClick={() => deleteRow(ladderItem.id)}
                    className="delete-row-btn"
                    disabled={ladderItems.length === 1}
                    title="Delete this row"
                  >
                    🗑️
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {!readOnly && (
        <div className="builder-actions">
          <button onClick={addNewRow} className="add-row-btn">
            <span className="plus-icon">+</span> Add New Item
          </button>
          
          {isReordering ? (
            <div className="reorder-confirm">
              <button onClick={reorderBySUDS} className="confirm-reorder-btn">
                ✓ Confirm Reorder by SUDS
              </button>
              <button onClick={() => setIsReordering(false)} className="cancel-btn">
                Cancel
              </button>
            </div>
          ) : (
            <button onClick={() => setIsReordering(true)} className="reorder-btn">
              ⇅ Reorder by SUDS
            </button>
          )}
          
          <button onClick={handleSubmit} className="submit-ladder-btn">
            {submitButtonText}
          </button>
        </div>
      )}
    </div>
  );
};

FearLadderBuilder.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  existingItems: PropTypes.array,
  readOnly: PropTypes.bool,
  submitButtonText: PropTypes.string
};

export default FearLadderBuilder;
