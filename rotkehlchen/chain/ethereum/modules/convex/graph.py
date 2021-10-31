QUERY_EVENTS = (
    """
    {
	withdrawals(where: {user_in: $addresses}){
      id
      poolid {
        id
      }
      amount
      timestamp
    }
    deposits(where: {user_in: $addresses}){
        id
        poolid {
        id
        }
        amount
        timestamp
    }
    }
    """
)